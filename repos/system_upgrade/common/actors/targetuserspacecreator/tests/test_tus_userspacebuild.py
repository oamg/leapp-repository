import os

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_userspacebuild
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import CopyFile, TargetUserSpaceInfo, UsedTargetRepositories, UsedTargetRepository

_DEDICATED_LEAPP_PARTITION_URL = 'https://access.redhat.com/solutions/5057391'


def _make_called_process_error(stderr='', stdout=''):
    return CalledProcessError(
        'Command failed.',
        ['dnf', 'install'],
        {'stdout': stdout, 'stderr': stderr, 'exit_code': 1}
    )


class RunSpy:
    """Record every invocation of the module-level ``run`` helper."""

    def __init__(self):
        self.calls = []

    def __call__(self, cmd, *args, **kwargs):
        self.calls.append(cmd)
        return {'stdout': '', 'stderr': ''}


class MockContext:
    def __init__(self, base_dir='/base'):
        self.base_dir = base_dir
        self.calls = []
        self.copy_to_calls = []
        self.copytree_to_calls = []
        self.remove_tree_calls = []

    def full_path(self, path):
        return os.path.join(self.base_dir, path.lstrip('/'))

    def call(self, cmd, *args, **kwargs):
        self.calls.append(cmd)
        return {'stdout': '', 'stderr': ''}

    def copy_to(self, src, dst):
        self.copy_to_calls.append((src, dst))

    def copytree_to(self, src, dst):
        self.copytree_to_calls.append((src, dst))

    def remove_tree(self, dst):
        self.remove_tree_calls.append(dst)


class MockCM:
    """Generic no-op context manager that records construction kwargs."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class MockNspawnActions:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir

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


class MockRepoFile:
    def __init__(self, data):
        self.data = data


class MockRepositoriesFacts:
    def __init__(self, repositories):
        self.repositories = repositories


class MockInputs:
    def __init__(self, pkg_manager_info=None, repositories_facts=None,
                 skip_rhsm=False, nogpgcheck=False, packages=None,
                 copy_files=None, rhui_info=None):
        self.pkg_manager_info = pkg_manager_info
        self.repositories_facts = repositories_facts
        self.skip_rhsm = skip_rhsm
        self.nogpgcheck = nogpgcheck
        self.packages = packages if packages is not None else []
        self.copy_files = copy_files if copy_files is not None else []
        self.rhui_info = rhui_info


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


def test_import_gpg_keys_no_dir(monkeypatch):
    logger = logger_mocked()
    context = MockContext()
    monkeypatch.setattr(api, 'current_logger', logger)
    monkeypatch.setattr(tus_userspacebuild, 'get_path_to_gpg_certs', lambda: '/no/such/dir')
    monkeypatch.setattr(os.path, 'isdir', lambda path: False)

    tus_userspacebuild._import_gpg_keys(context, '/installroot')

    assert not context.calls
    assert len(logger.warnmsg) == 1


def test_import_gpg_keys_with_keys(monkeypatch):
    context = MockContext()
    certs_dir = '/etc/leapp/gpg'
    monkeypatch.setattr(tus_userspacebuild, 'get_path_to_gpg_certs', lambda: certs_dir)
    monkeypatch.setattr(os.path, 'isdir', lambda path: True)
    monkeypatch.setattr(os, 'listdir', lambda path: ['key-b', 'key-a'])

    tus_userspacebuild._import_gpg_keys(context, '/installroot')

    assert context.calls == [
        ['rpm', '--root', '/installroot', '--import', os.path.join(certs_dir, 'key-a')],
        ['rpm', '--root', '/installroot', '--import', os.path.join(certs_dir, 'key-b')],
    ]


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
    err = _make_called_process_error(stderr=stderr)

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
    err = _make_called_process_error(stderr=stderr)
    inputs = MockInputs()

    with pytest.raises(StopActorExecutionError) as exc_info:
        tus_userspacebuild._diagnose_dnf_failure(err, inputs)

    assert '1GB' in exc_info.value.details['hint']


def test_diagnose_dnf_failure_proxy_in_pkg_manager(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_distro='rhel', dst_distro='rhel'))
    err = _make_called_process_error(stderr='some generic dnf error')
    inputs = MockInputs(pkg_manager_info=MockPkgManagerInfo(configured_proxies=['http://proxy']))

    with pytest.raises(StopActorExecutionError) as exc_info:
        tus_userspacebuild._diagnose_dnf_failure(err, inputs)

    details = exc_info.value.details
    assert 'proxy' in details['hints']
    assert details['stderr'] == 'some generic dnf error'


def test_diagnose_dnf_failure_proxy_in_repo(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_distro='rhel', dst_distro='rhel'))
    err = _make_called_process_error(stderr='some generic dnf error')
    repo_file = MockRepoFile([MockRepoData(proxy='http://proxy', enabled=True)])
    inputs = MockInputs(repositories_facts=MockRepositoriesFacts([repo_file]))

    with pytest.raises(StopActorExecutionError) as exc_info:
        tus_userspacebuild._diagnose_dnf_failure(err, inputs)

    assert 'repository configuration file' in exc_info.value.details['hints']


def test_diagnose_dnf_failure_centos_to_rhel(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_distro='centos', dst_distro='rhel'))
    err = _make_called_process_error(stderr='some generic dnf error')
    inputs = MockInputs()

    with pytest.raises(StopActorExecutionError) as exc_info:
        tus_userspacebuild._diagnose_dnf_failure(err, inputs)

    hints = exc_info.value.details['hints']
    assert 'Centos Stream to Red Hat Enterprise Linux' in hints


def test_copy_files_to_userspace_dst_defaults_to_src(monkeypatch):
    context = MockContext()
    monkeypatch.setattr(os.path, 'isdir', lambda path: False)
    copy_file = CopyFile(src='/host/file')

    tus_userspacebuild._copy_files_to_userspace(context, [copy_file])

    assert copy_file.dst == '/host/file'
    assert context.copy_to_calls == [('/host/file', '/host/file')]


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
    inputs = MockInputs(nogpgcheck=False, packages=['dnf'], copy_files=[], rhui_info=None)
    used_repos = UsedTargetRepositories(repos=[UsedTargetRepository(repoid='r1')])

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver='9.6'))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(tus_userspacebuild, 'run', run_spy)
    monkeypatch.setattr(tus_userspacebuild, '_persistent_cache_push', lambda *a, **k: None)
    monkeypatch.setattr(tus_userspacebuild, '_persistent_cache_pull', lambda *a, **k: None)
    monkeypatch.setattr(tus_userspacebuild, '_create_target_userspace_dir', lambda *a, **k: None)
    monkeypatch.setattr(tus_userspacebuild, '_import_gpg_keys', lambda *a, **k: None)
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
