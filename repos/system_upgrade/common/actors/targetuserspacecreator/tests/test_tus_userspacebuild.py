import contextlib

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_layout, tus_userspacebuild
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import (
    RepositoriesFacts,
    RepositoryData,
    RepositoryFile,
    TargetUserSpaceInfo,
    UsedTargetRepositories,
    UsedTargetRepository
)


def _cpe(stdout='', stderr=''):
    return CalledProcessError('boom', ['dnf'], {'exit_code': 1, 'stdout': stdout, 'stderr': stderr})


class _Inputs:
    def __init__(self, skip_rhsm=False, nogpgcheck=False, packages=None, copy_files=None,
                 rhui_info=None, pkg_manager_info=None, repositories_facts=None):
        self.skip_rhsm = skip_rhsm
        self.nogpgcheck = nogpgcheck
        self.packages = packages or ['dnf']
        self.copy_files = copy_files or []
        self.rhui_info = rhui_info
        self.pkg_manager_info = pkg_manager_info
        self.repositories_facts = repositories_facts


class _PkgManagerInfo:
    def __init__(self, configured_proxies):
        self.configured_proxies = configured_proxies


class _Setup:
    def __init__(self, bootstrap):
        self.bootstrap_target_client = bootstrap


class _RhuiInfo:
    def __init__(self, bootstrap):
        self.target_client_setup_info = _Setup(bootstrap)


class _NullCM:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


# --------------------------------------------------------------------------- #
# _build_dnf_install_cmd
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize('skip_rhsm,nogpgcheck', [
    (False, False), (True, False), (False, True), (True, True),
])
def test_build_dnf_install_cmd(skip_rhsm, nogpgcheck):
    cmd = tus_userspacebuild._build_dnf_install_cmd(
        installroot='/root', releasever='9.6',
        repoids=['baseos', 'appstream'], skip_rhsm=skip_rhsm, nogpgcheck=nogpgcheck,
        packages=['dnf', 'util-linux'],
    )

    assert cmd[:3] == ['dnf', 'install', '-y']
    assert ('--nogpgcheck' in cmd) is nogpgcheck
    assert ('--disableplugin' in cmd and 'subscription-manager' in cmd) is skip_rhsm
    assert '--setopt=module_platform_id=platform:el9' in cmd
    assert cmd[cmd.index('--releasever') + 1] == '9.6'
    assert cmd[cmd.index('--installroot') + 1] == '/root'
    assert '--disablerepo' in cmd and '*' in cmd
    # every repoid enabled, packages last
    assert cmd.count('--enablerepo') == 2
    assert cmd[-2:] == ['dnf', 'util-linux']


# --------------------------------------------------------------------------- #
# _diagnose_dnf_failure - always raises; hint selection
# --------------------------------------------------------------------------- #
def test_diagnose_disk_space_hint():
    # Disk-space detection reads *stderr*; it raises before any distro lookup.
    err = _cpe(stderr='Disk Requirements:\n  At least 500MB more space needed on the /var filesystem')
    with pytest.raises(StopActorExecutionError) as excinfo:
        tus_userspacebuild._diagnose_dnf_failure(err, _Inputs())

    hint = excinfo.value.details['hint']
    assert '500MB' in hint
    assert tus_userspacebuild._DEDICATED_LEAPP_PARTITION_URL in hint


def test_diagnose_proxy_in_dnf_conf_hint(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_distro='rhel', dst_distro='rhel'))
    pkg_manager_info = _PkgManagerInfo(configured_proxies=['http://proxy'])

    with pytest.raises(StopActorExecutionError) as excinfo:
        tus_userspacebuild._diagnose_dnf_failure(
            _cpe(stderr='some other error'), _Inputs(pkg_manager_info=pkg_manager_info))

    assert 'YUM/DNF configuration file' in excinfo.value.details['hints']


def test_diagnose_proxy_in_repofile_hint(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_distro='rhel', dst_distro='rhel'))
    repositories_facts = RepositoriesFacts(repositories=[
        RepositoryFile(file='/etc/yum.repos.d/x.repo', data=[
            RepositoryData(repoid='r', name='R', proxy='http://proxy', enabled=True),
        ]),
    ])

    with pytest.raises(StopActorExecutionError) as excinfo:
        tus_userspacebuild._diagnose_dnf_failure(
            _cpe(stderr='boom'), _Inputs(repositories_facts=repositories_facts))

    assert 'repository configuration file' in excinfo.value.details['hints']


def test_diagnose_centos_to_rhel_hint(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_distro='centos', dst_distro='rhel'))

    with pytest.raises(StopActorExecutionError) as excinfo:
        tus_userspacebuild._diagnose_dnf_failure(_cpe(stderr='boom'), _Inputs())

    assert 'might not yet have been released' in excinfo.value.details['hints']


def test_diagnose_no_repositories_facts_does_not_crash(monkeypatch):
    # Regression: repositories_facts is a single message or None, not a list.
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_distro='rhel', dst_distro='rhel'))

    with pytest.raises(StopActorExecutionError):
        tus_userspacebuild._diagnose_dnf_failure(_cpe(stderr='boom'), _Inputs(repositories_facts=None))


# --------------------------------------------------------------------------- #
# _import_gpg_keys
# --------------------------------------------------------------------------- #
class _CallRecorder:
    def __init__(self):
        self.calls = []

    def call(self, cmd, *args, **kwargs):
        self.calls.append(cmd)
        return {'stdout': []}

    def full_path(self, path):
        return '/overlay' + path


def test_import_gpg_keys_sorted(monkeypatch):
    context = _CallRecorder()
    monkeypatch.setattr(tus_userspacebuild, 'get_path_to_gpg_certs', lambda: '/certs')
    monkeypatch.setattr(tus_userspacebuild.os.path, 'isdir', lambda p: True)
    monkeypatch.setattr(tus_userspacebuild.os, 'listdir', lambda p: ['keyB', 'keyA'])

    tus_userspacebuild._import_gpg_keys(context, '/installroot')

    assert context.calls == [
        ['rpm', '--root', '/installroot', '--import', '/certs/keyA'],
        ['rpm', '--root', '/installroot', '--import', '/certs/keyB'],
    ]


def test_import_gpg_keys_missing_dir_is_noop(monkeypatch):
    context = _CallRecorder()
    monkeypatch.setattr(tus_userspacebuild, 'get_path_to_gpg_certs', lambda: '/certs')
    monkeypatch.setattr(tus_userspacebuild.os.path, 'isdir', lambda p: False)

    tus_userspacebuild._import_gpg_keys(context, '/installroot')

    assert not context.calls


# --------------------------------------------------------------------------- #
# build() orchestration
# --------------------------------------------------------------------------- #
class _BuildContext:
    def __init__(self):
        self.calls = []

    def call(self, cmd, *args, **kwargs):
        self.calls.append(cmd)
        return {'stdout': []}

    def full_path(self, path):
        return '/overlay' + path


class _UsContext:
    def __init__(self, base_dir):
        self.base_dir = base_dir

    def call(self, cmd, *args, **kwargs):
        return {'stdout': []}


def _layout():
    return tus_layout.Layout(
        container_root='/var/lib/leapp',
        userspace_path='/var/lib/leapp/el9userspace',
        scratch_dir='/var/lib/leapp/scratch',
        mounts_dir='/var/lib/leapp/scratch/mounts',
        installroot_overlay_mountpoint='/el9target',
        persistent_pkg_cache_path='/var/lib/leapp/persistent_package_cache',
        scratch_reserve=1,
    )


def _used_repos():
    return UsedTargetRepositories(repos=[UsedTargetRepository(repoid='baseos')])


def _patch_build_commons(monkeypatch, events):
    monkeypatch.setattr(tus_userspacebuild, 'run', lambda cmd: events.append(('run', cmd)))
    monkeypatch.setattr(tus_userspacebuild, '_persistent_cache_push',
                        lambda cache, us: events.append(('push',)))
    monkeypatch.setattr(tus_userspacebuild, '_persistent_cache_pull',
                        lambda cache, us: events.append(('pull',)))
    monkeypatch.setattr(tus_userspacebuild, '_create_target_userspace_dir',
                        lambda path: events.append(('mkdir', path)))
    monkeypatch.setattr(tus_userspacebuild, '_import_gpg_keys',
                        lambda ctx, ir: events.append(('gpg',)))
    monkeypatch.setattr(tus_userspacebuild.tus_repoaccess, 'prep_repository_access',
                        lambda ctx, path: events.append(('prep', path)))
    monkeypatch.setattr(tus_userspacebuild.dnfplugin, 'install',
                        lambda path: events.append(('plugin', path)))
    monkeypatch.setattr(tus_userspacebuild.rhsm, 'set_container_mode',
                        lambda ctx: events.append(('container_mode',)))
    monkeypatch.setattr(tus_userspacebuild, 'get_target_version', lambda: '9.6')
    monkeypatch.setattr(tus_userspacebuild.mounting, 'BindMount',
                        lambda source, target: _NullCM())

    @contextlib.contextmanager
    def fake_nspawn(base_dir):
        events.append(('nspawn', base_dir))
        yield _UsContext(base_dir)

    monkeypatch.setattr(tus_userspacebuild.mounting, 'NspawnActions', fake_nspawn)


def test_build_happy_path(monkeypatch):
    events = []
    _patch_build_commons(monkeypatch, events)

    result = tus_userspacebuild.build(_BuildContext(), _layout(), _Inputs(nogpgcheck=False), _used_repos())

    assert isinstance(result, TargetUserSpaceInfo)
    assert result.path == '/var/lib/leapp/el9userspace'
    assert result.scratch == '/var/lib/leapp/scratch'
    assert result.mounts == '/var/lib/leapp/scratch/mounts'

    kinds = [e[0] for e in events]
    assert 'gpg' in kinds
    assert ('plugin', '/var/lib/leapp/el9userspace') in events
    assert ('prep', '/var/lib/leapp/el9userspace') in events
    assert ('container_mode',) in events
    # cache is pushed before the userspace is wiped, pulled after it is recreated
    assert kinds.index('push') < kinds.index('pull')


def test_build_skips_gpg_when_nogpgcheck(monkeypatch):
    events = []
    _patch_build_commons(monkeypatch, events)

    tus_userspacebuild.build(_BuildContext(), _layout(), _Inputs(nogpgcheck=True), _used_repos())

    assert 'gpg' not in [e[0] for e in events]


def test_build_cleanup_only_when_not_bootstrapping(monkeypatch):
    events = []
    _patch_build_commons(monkeypatch, events)
    monkeypatch.setattr(tus_userspacebuild.tus_rhui, 'cleanup_injected_repofiles',
                        lambda ctx, ri: events.append(('cleanup',)))

    tus_userspacebuild.build(_BuildContext(), _layout(),
                             _Inputs(rhui_info=_RhuiInfo(bootstrap=False)), _used_repos())

    assert ('cleanup',) in events


def test_build_no_cleanup_when_bootstrapping(monkeypatch):
    events = []
    _patch_build_commons(monkeypatch, events)
    monkeypatch.setattr(tus_userspacebuild.tus_rhui, 'cleanup_injected_repofiles',
                        lambda ctx, ri: events.append(('cleanup',)))

    tus_userspacebuild.build(_BuildContext(), _layout(),
                             _Inputs(rhui_info=_RhuiInfo(bootstrap=True)), _used_repos())

    assert ('cleanup',) not in events


def test_build_diagnoses_dnf_failure(monkeypatch):
    events = []
    _patch_build_commons(monkeypatch, events)

    class _FailingContext(_BuildContext):
        def call(self, cmd, *args, **kwargs):
            if cmd[:2] == ['dnf', 'install']:
                raise _cpe(stderr='Disk Requirements:\n  At least 100MB more space needed on the /var filesystem')
            return {'stdout': []}

    with pytest.raises(StopActorExecutionError) as excinfo:
        tus_userspacebuild.build(_FailingContext(), _layout(), _Inputs(), _used_repos())

    assert tus_userspacebuild._DEDICATED_LEAPP_PARTITION_URL in excinfo.value.details['hint']
