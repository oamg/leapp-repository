import os

import pytest
from test_tus_mock_utils import make_cpe, MockContext, MockInputData, MockNspawnActions, RunSpy

from leapp import models
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_userspacebuild
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import CopyFile, TargetUserSpaceInfo, UsedTargetRepositories, UsedTargetRepository

_DEDICATED_LEAPP_PARTITION_URL = 'https://access.redhat.com/solutions/5057391'

# keyed by whether PQC key should be included
_IMPORT_KEYFILES = {
    False: ['/keys/root-key'],
    True: ['/keys/root-key', '/keys/pqc/pqc-key'],
}
_PQRPM_RPMKEYS = '/usr/lib/pqrpm/bin/rpmkeys'


class MockCM:
    """Generic no-op context manager that records construction kwargs."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class MockPkgManagerInfo:
    def __init__(self, configured_proxies=None):
        self.configured_proxies = configured_proxies or []


class MockRepoData:
    def __init__(self, proxy=None, enabled=True):
        self.proxy = proxy
        self.enabled = enabled


class MockRepoFactsFile:
    def __init__(self, data):
        self.data = data


class MockRepositoriesFacts:
    def __init__(self, repositories):
        self.repositories = repositories


class MockLayout:
    def __init__(self):
        self.persistent_pkg_cache_path = '/var/lib/leapp/persistent_package_cache'
        self.userspace_path = '/var/lib/leapp/el9userspace'
        self.scratch_dir = '/var/lib/leapp/scratch'
        self.mounts_dir = '/var/lib/leapp/scratch/mounts'
        self.installroot_overlay_mountpoint = '/el9target'


@pytest.mark.parametrize(
    ('envars', 'expected'),
    [
        ({'LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE': '1'}, True),
        ({'LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE': '0'}, False),
        ({'LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE': 'yes'}, False),
        ({}, False),
    ]
)
def test_persistent_cache_enabled(monkeypatch, envars, expected):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(envars=envars))
    assert tus_userspacebuild._persistent_cache_enabled() == expected


def test_persistent_cache_pull_disabled(monkeypatch):
    run_spy = RunSpy()
    monkeypatch.setattr(tus_userspacebuild, 'run', run_spy)
    monkeypatch.setattr(tus_userspacebuild, '_persistent_cache_enabled', lambda: False)

    tus_userspacebuild._persistent_cache_pull('/cache', '/installroot')

    assert run_spy.calls == [['rm', '-rf', '/cache']]


def test_persistent_cache_pull_enabled_missing_cache(monkeypatch):
    run_spy = RunSpy()
    monkeypatch.setattr(tus_userspacebuild, 'run', run_spy)
    monkeypatch.setattr(tus_userspacebuild, '_persistent_cache_enabled', lambda: True)
    monkeypatch.setattr(os.path, 'isdir', lambda path: False)

    tus_userspacebuild._persistent_cache_pull('/cache', '/installroot')

    # The early return when the cache dir is missing also skips the final
    # unconditional cleanup, so no command is executed at all.
    assert not run_spy.calls


def test_persistent_cache_pull_enabled_present(monkeypatch):
    run_spy = RunSpy()
    moves = []
    monkeypatch.setattr(tus_userspacebuild, 'run', run_spy)
    monkeypatch.setattr(tus_userspacebuild, '_persistent_cache_enabled', lambda: True)
    monkeypatch.setattr(os.path, 'isdir', lambda path: True)
    monkeypatch.setattr(os.path, 'exists', lambda path: True)
    monkeypatch.setattr(tus_userspacebuild.shutil, 'move', lambda src, dst: moves.append((src, dst)))

    tus_userspacebuild._persistent_cache_pull('/cache', '/installroot')

    dst = os.path.join('/installroot', 'var', 'cache', 'dnf')
    assert ['rm', '-rf', dst] in run_spy.calls
    assert moves == [('/cache', dst)]
    assert run_spy.calls[-1] == ['rm', '-rf', '/cache']


def test_persistent_cache_push_disabled(monkeypatch):
    run_spy = RunSpy()
    monkeypatch.setattr(tus_userspacebuild, 'run', run_spy)
    monkeypatch.setattr(tus_userspacebuild, '_persistent_cache_enabled', lambda: False)

    tus_userspacebuild._persistent_cache_push('/cache', '/installroot')

    assert not run_spy.calls


def test_persistent_cache_push_enabled(monkeypatch):
    run_spy = RunSpy()
    moves = []
    monkeypatch.setattr(tus_userspacebuild, 'run', run_spy)
    monkeypatch.setattr(tus_userspacebuild, '_persistent_cache_enabled', lambda: True)
    monkeypatch.setattr(os.path, 'exists', lambda path: True)
    monkeypatch.setattr(tus_userspacebuild.shutil, 'move', lambda src, dst: moves.append((src, dst)))

    tus_userspacebuild._persistent_cache_push('/cache', '/installroot')

    src = os.path.join('/installroot', 'var', 'cache', 'dnf')
    assert run_spy.calls == [['rm', '-rf', '/cache']]
    assert moves == [(src, '/cache')]


class _ImportKeysContext:
    """Records emitted commands and can fail on a chosen binary."""

    def __init__(self, fail_on=None, stderr=''):
        self.calls = []
        self._fail_on = fail_on
        self._stderr = stderr

    def call(self, cmd, **dummy_kwargs):
        self.calls.append(cmd)
        if self._fail_on and cmd[0] == self._fail_on:
            result = {'stdout': '', 'stderr': self._stderr, 'exit_code': 1, 'signal': None, 'pid': 1}
            raise CalledProcessError('failed', cmd, result)
        return {'exit_code': 0}

    def binaries(self):
        return [cmd[0] for cmd in self.calls]

    def imported_paths(self, binary):
        return [cmd[cmd.index('--import') + 1] for cmd in self.calls if cmd[0] == binary]


def _installed_rpms(pqrpm_installed):
    items = [models.RPM(
        name='rpm', version='4.17.1', release='1', epoch='0', packager='', arch='x86_64', pgpsig=''
    )]
    if pqrpm_installed:
        items.append(models.RPM(
            name='pqrpm', version='1.0', release='1', epoch='0', packager='', arch='x86_64', pgpsig=''
        ))
    return models.InstalledRPM(items=items)


def _setup_import_keys(monkeypatch, target_version, keyfiles_by_scope, pqrpm_installed=False):
    """Stub the version and keyfile discovery used by _import_gpg_keys_to_scratch."""
    monkeypatch.setattr(
        tus_userspacebuild.api, 'current_actor',
        CurrentActorMocked(dst_ver=target_version, msgs=[_installed_rpms(pqrpm_installed)])
    )
    monkeypatch.setattr(
        tus_userspacebuild, 'iter_gpg_keyfiles',
        lambda include_pqc: iter(keyfiles_by_scope[include_pqc])
    )


@pytest.mark.parametrize('target_version, expected_pqrpm_imports', [
    # on 10.0 there is no PQC support in rpm, so pqrpm import must not be attempted
    ('10.0', []),
    # newer targets import all (v4 + pqc) keys into the separate pqrpmdb
    ('10.1', ['/keys/root-key', '/keys/pqc/pqc-key']),
])
def test_import_gpg_keys_to_scratch_version_gating(monkeypatch, target_version, expected_pqrpm_imports):
    _setup_import_keys(monkeypatch, target_version, _IMPORT_KEYFILES, pqrpm_installed=True)
    context = _ImportKeysContext()

    tus_userspacebuild._import_gpg_keys_to_scratch(context, '/instroot')

    assert context.imported_paths('rpm') == ['/keys/root-key']
    assert context.imported_paths(_PQRPM_RPMKEYS) == expected_pqrpm_imports
    # keys are always imported into the given install root, regardless of arg order
    for cmd in context.calls:
        assert '--root' in cmd
        assert cmd[cmd.index('--root') + 1] == '/instroot'


def test_import_gpg_keys_to_scratch_skips_pqrpm_when_not_installed(monkeypatch):
    # rpmkeys used for the pqrpmdb import comes from the source system's 'pqrpm'
    # package; without it installed there is no binary to import with, so the
    # pqrpm import is skipped even on a PQC-capable target
    _setup_import_keys(monkeypatch, '10.1', _IMPORT_KEYFILES, pqrpm_installed=False)
    context = _ImportKeysContext()

    tus_userspacebuild._import_gpg_keys_to_scratch(context, '/instroot')

    assert context.imported_paths('rpm') == ['/keys/root-key']
    assert context.imported_paths(_PQRPM_RPMKEYS) == []


@pytest.mark.parametrize('fail_on, stderr', [
    # a rpm import failure is always fatal
    ('rpm', 'rpm import failure'),
    # a pqrpm import failure other than the missing binary is fatal
    (_PQRPM_RPMKEYS, 'some other rpmkeys failure'),
])
def test_import_gpg_keys_to_scratch_import_error_raises(monkeypatch, fail_on, stderr):
    _setup_import_keys(monkeypatch, '10.1', _IMPORT_KEYFILES, pqrpm_installed=True)
    context = _ImportKeysContext(fail_on=fail_on, stderr=stderr)

    with pytest.raises(CalledProcessError):
        tus_userspacebuild._import_gpg_keys_to_scratch(context, '/instroot')


@pytest.mark.parametrize('nogpgcheck', [False, True])
def test_build_dnf_install_cmd(nogpgcheck):
    cmd = tus_userspacebuild._build_dnf_install_cmd(
        '/installroot', '9.6', ['r1', 'r2'], False, nogpgcheck, ['pkgA']
    )

    expected = ['dnf', 'install', '-y']
    if nogpgcheck:
        expected.append('--nogpgcheck')
    expected += [
        '--setopt=module_platform_id=platform:el9',
        '--setopt=keepcache=1',
        '--releasever', '9.6',
        '--installroot', '/installroot',
        '--disablerepo', '*',
        '--enablerepo', 'r1',
        '--enablerepo', 'r2',
        'pkgA',
    ]
    assert cmd == expected


def test_build_dnf_install_cmd_skip_rhsm():
    cmd = tus_userspacebuild._build_dnf_install_cmd(
        '/installroot', '9.6', [], True, False, []
    )

    assert cmd == [
        'dnf', 'install', '-y',
        '--setopt=module_platform_id=platform:el9',
        '--setopt=keepcache=1',
        '--releasever', '9.6',
        '--disableplugin', 'subscription-manager',
        '--installroot', '/installroot',
        '--disablerepo', '*',
    ]


def test_raise_insufficient_space_error():
    stderr = (
        'Disk Requirements:\n'
        '  At least 200MB more space needed on the / filesystem.\n'
    )
    err = make_cpe(stderr=stderr)

    with pytest.raises(StopActorExecutionError) as exc_info:
        tus_userspacebuild._raise_insufficient_space_error(err)

    hint = exc_info.value.details['hint']
    assert '200MB' in hint
    assert _DEDICATED_LEAPP_PARTITION_URL in hint


def test_diagnose_dnf_failure_insufficient_space(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    stderr = (
        'Disk Requirements:\n'
        '  At least 1GB more space needed on the / filesystem.\n'
    )
    err = make_cpe(stderr=stderr)
    inputs = MockInputData()

    with pytest.raises(StopActorExecutionError) as exc_info:
        tus_userspacebuild._diagnose_dnf_failure(err, inputs)

    assert '1GB' in exc_info.value.details['hint']


def test_diagnose_dnf_failure_proxy_in_pkg_manager(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_distro='rhel', dst_distro='rhel'))
    err = make_cpe(stderr='some generic dnf error')
    inputs = MockInputData(pkg_manager_info=MockPkgManagerInfo(configured_proxies=['http://proxy']))

    with pytest.raises(StopActorExecutionError) as exc_info:
        tus_userspacebuild._diagnose_dnf_failure(err, inputs)

    details = exc_info.value.details
    assert 'proxy' in details['hint']
    assert details['stderr'] == 'some generic dnf error'


def test_diagnose_dnf_failure_proxy_in_repo(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_distro='rhel', dst_distro='rhel'))
    err = make_cpe(stderr='some generic dnf error')
    repo_file = MockRepoFactsFile([MockRepoData(proxy='http://proxy', enabled=True)])
    inputs = MockInputData(repositories_facts=MockRepositoriesFacts([repo_file]))

    with pytest.raises(StopActorExecutionError) as exc_info:
        tus_userspacebuild._diagnose_dnf_failure(err, inputs)

    assert 'repository configuration file' in exc_info.value.details['hint']


def test_diagnose_dnf_failure_centos_to_rhel(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_distro='centos', dst_distro='rhel'))
    err = make_cpe(stderr='some generic dnf error')
    inputs = MockInputData()

    with pytest.raises(StopActorExecutionError) as exc_info:
        tus_userspacebuild._diagnose_dnf_failure(err, inputs)

    hint = exc_info.value.details['hint']
    assert 'Centos Stream to Red Hat Enterprise Linux' in hint


def test_copy_files_to_userspace_directory(monkeypatch):
    context = MockContext()
    monkeypatch.setattr(os.path, 'isdir', lambda path: True)
    copy_file = CopyFile(src='/host/dir', dst='/target/dir')

    tus_userspacebuild._copy_files_to_userspace(context, [copy_file])

    assert context.remove_tree_calls == ['/target/dir']
    assert context.copytree_to_calls == [('/host/dir', '/target/dir')]
    assert not context.copy_to_calls


def test_copy_files_to_userspace_regular_file(monkeypatch):
    context = MockContext()
    monkeypatch.setattr(os.path, 'isdir', lambda path: False)
    copy_file = CopyFile(src='/host/file', dst='/target/file')

    tus_userspacebuild._copy_files_to_userspace(context, [copy_file])

    assert context.copy_to_calls == [('/host/file', '/target/file')]


def test_create_target_userspace_dir_success(monkeypatch):
    created = []
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(tus_userspacebuild.utils, 'makedirs', created.append)

    tus_userspacebuild._create_target_userspace_dir('/some/path')

    assert created == ['/some/path']


def test_create_target_userspace_dir_failure(monkeypatch):
    def _raise(path):
        raise OSError('boom')

    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(tus_userspacebuild.utils, 'makedirs', _raise)

    with pytest.raises(StopActorExecutionError) as exc_info:
        tus_userspacebuild._create_target_userspace_dir('/some/path')

    assert '/some/path' in exc_info.value.details['hint']


def test_build_returns_target_userspace_info(monkeypatch):
    run_spy = RunSpy()
    context = MockContext()
    layout = MockLayout()
    inputs = MockInputData(nogpgcheck=False, packages=['dnf'], copy_files=[], rhui_info=None)
    used_repos = UsedTargetRepositories(repos=[UsedTargetRepository(repoid='r1')])

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver='9.6'))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(tus_userspacebuild, 'run', run_spy)
    monkeypatch.setattr(tus_userspacebuild, '_persistent_cache_push', lambda *a, **k: None)
    monkeypatch.setattr(tus_userspacebuild, '_persistent_cache_pull', lambda *a, **k: None)
    monkeypatch.setattr(tus_userspacebuild, '_create_target_userspace_dir', lambda *a, **k: None)
    monkeypatch.setattr(tus_userspacebuild, '_import_gpg_keys_to_scratch', lambda *a, **k: None)
    monkeypatch.setattr(tus_userspacebuild.mounting, 'BindMount', MockCM)
    monkeypatch.setattr(tus_userspacebuild.mounting, 'NspawnActions', MockNspawnActions)
    monkeypatch.setattr(tus_userspacebuild.tus_repoaccess, 'prep_repository_access', lambda *a, **k: None)
    monkeypatch.setattr(tus_userspacebuild.dnfplugin, 'install', lambda *a, **k: None)
    monkeypatch.setattr(tus_userspacebuild.rhsm, 'set_container_mode', lambda *a, **k: None)

    result = tus_userspacebuild.build(context, layout, inputs, used_repos)

    assert isinstance(result, TargetUserSpaceInfo)
    assert result.path == layout.userspace_path
    assert result.scratch == layout.scratch_dir
    assert result.mounts == layout.mounts_dir
    dnf_install_cmds = [cmd for cmd in context.calls if cmd[:3] == ['dnf', 'install', '-y']]
    assert len(dnf_install_cmds) == 1
