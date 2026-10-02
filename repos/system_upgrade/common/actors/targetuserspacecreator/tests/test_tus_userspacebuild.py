import contextlib

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_userspacebuild
from leapp.libraries.stdlib import CalledProcessError
from leapp.models import TargetUserSpaceInfo


def _cpe(stdout='', stderr=''):
    return CalledProcessError('boom', ['dnf'], {'exit_code': 1, 'stdout': stdout, 'stderr': stderr})


class _Inputs(object):
    def __init__(self, skip_rhsm=False, nogpgcheck=False, packages=None, copy_files=None,
                 rhui_info=None, pkg_manager_info=None, repositories_facts=None):
        self.skip_rhsm = skip_rhsm
        self.nogpgcheck = nogpgcheck
        self.packages = packages or ['dnf']
        self.copy_files = copy_files or []
        self.rhui_info = rhui_info
        self.pkg_manager_info = pkg_manager_info
        self.repositories_facts = repositories_facts


# --------------------------------------------------------------------------- #
# _build_dnf_install_cmd
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize('skip_rhsm,nogpgcheck', [
    (False, False), (True, False), (False, True), (True, True),
])
def test_build_dnf_install_cmd(skip_rhsm, nogpgcheck):
    cmd = tus_userspacebuild._build_dnf_install_cmd(
        installroot='/root', target_major='9', releasever='9.6',
        repoids=['baseos', 'appstream'], skip_rhsm=skip_rhsm, nogpgcheck=nogpgcheck,
        packages=['dnf', 'util-linux'],
    )

    assert cmd[:3] == ['dnf', 'install', '-y']
    assert ('--nogpgcheck' in cmd) is nogpgcheck
    assert ('--disableplugin' in cmd and 'subscription-manager' in cmd) is skip_rhsm
    assert '--setopt=module_platform_id=platform:el9' in cmd
    assert '--releasever' in cmd and '9.6' in cmd
    assert cmd[cmd.index('--installroot') + 1] == '/root'
    assert '--disablerepo' in cmd and '*' in cmd
    # every repoid enabled, packages last
    assert cmd.count('--enablerepo') == 2
    assert cmd[-2:] == ['dnf', 'util-linux']


# --------------------------------------------------------------------------- #
# _diagnose_dnf_failure - always raises; hint selection
# --------------------------------------------------------------------------- #
def test_diagnose_disk_space_hint():
    with pytest.raises(StopActorExecutionError) as err:
        tus_userspacebuild._diagnose_dnf_failure(
            _cpe(stdout='Error: more space needed on the /var/lib filesystem'), _Inputs())
    assert err.value.details['link'] == tus_userspacebuild._DEDICATED_LEAPP_PARTITION_URL


def test_diagnose_proxy_in_dnf_conf_hint(monkeypatch):
    monkeypatch.setattr(tus_userspacebuild, 'get_source_distro_id', lambda: 'rhel')
    monkeypatch.setattr(tus_userspacebuild, 'get_target_distro_id', lambda: 'rhel')
    pkg_manager_info = type('P', (), {'configured_proxies': ['http://proxy']})()
    with pytest.raises(StopActorExecutionError) as err:
        tus_userspacebuild._diagnose_dnf_failure(_cpe(stdout='some other error'),
                                                 _Inputs(pkg_manager_info=pkg_manager_info))
    assert any('proxy is configured in dnf.conf' in h for h in err.value.details['hints'])


def test_diagnose_proxy_in_repofile_hint(monkeypatch):
    monkeypatch.setattr(tus_userspacebuild, 'get_source_distro_id', lambda: 'rhel')
    monkeypatch.setattr(tus_userspacebuild, 'get_target_distro_id', lambda: 'rhel')
    repo = type('R', (), {'proxy': 'http://proxy'})()
    repofile = type('RF', (), {'data': [repo]})()
    repositories_facts = type('RFacts', (), {'repositories': [repofile]})()
    with pytest.raises(StopActorExecutionError) as err:
        tus_userspacebuild._diagnose_dnf_failure(_cpe(stdout='boom'),
                                                 _Inputs(repositories_facts=repositories_facts))
    assert any('proxy is configured in a .repo file' in h for h in err.value.details['hints'])


def test_diagnose_centos_to_rhel_hint(monkeypatch):
    monkeypatch.setattr(tus_userspacebuild, 'get_source_distro_id', lambda: 'centos')
    monkeypatch.setattr(tus_userspacebuild, 'get_target_distro_id', lambda: 'rhel')
    with pytest.raises(StopActorExecutionError) as err:
        tus_userspacebuild._diagnose_dnf_failure(_cpe(stdout='boom'), _Inputs())
    assert any('target RHEL version may not be released' in h for h in err.value.details['hints'])


# --------------------------------------------------------------------------- #
# _import_gpg_keys
# --------------------------------------------------------------------------- #
def test_import_gpg_keys(monkeypatch):
    calls = []
    context = type('C', (), {'call': lambda self, cmd: calls.append(cmd)})()
    monkeypatch.setattr(tus_userspacebuild, 'get_path_to_gpg_certs', lambda: '/certs')
    monkeypatch.setattr(tus_userspacebuild.os.path, 'isdir', lambda p: True)
    monkeypatch.setattr(tus_userspacebuild.os, 'listdir', lambda p: ['keyB', 'keyA'])

    tus_userspacebuild._import_gpg_keys(context, '/installroot')

    # sorted, each imported into the installroot rpm db
    assert calls == [
        ['rpm', '--root', '/installroot', '--import', '/certs/keyA'],
        ['rpm', '--root', '/installroot', '--import', '/certs/keyB'],
    ]


# --------------------------------------------------------------------------- #
# build() orchestration
# --------------------------------------------------------------------------- #
class _BuildContext(object):
    def __init__(self):
        self.calls = []
        self.copied_from = []

    def call(self, cmd, *a, **k):
        self.calls.append(cmd)
        return {'stdout': []}

    def remove_tree(self, path):
        pass

    def makedirs(self, path, mode=0o777, exists_ok=True):
        pass

    def copytree_from(self, src, dst):
        self.copied_from.append((src, dst))

    def copy_from(self, src, dst):
        self.copied_from.append((src, dst))

    def full_path(self, path):
        return '/overlay' + path


def _patch_build_commons(monkeypatch, events):
    monkeypatch.setattr(tus_userspacebuild, 'run', lambda cmd: events.append(('run', cmd)))
    monkeypatch.setattr(tus_userspacebuild.tus_layout, 'persistent_cache_pull',
                        lambda ctx, layout, ir: events.append(('pull',)))
    monkeypatch.setattr(tus_userspacebuild.tus_layout, 'persistent_cache_push',
                        lambda ctx, layout, ir: events.append(('push',)))
    monkeypatch.setattr(tus_userspacebuild, '_import_gpg_keys',
                        lambda ctx, ir: events.append(('gpg',)))
    monkeypatch.setattr(tus_userspacebuild.tus_repoaccess, 'prep_repository_access',
                        lambda ctx, path: events.append(('prep',)))
    monkeypatch.setattr(tus_userspacebuild.dnfplugin, 'install',
                        lambda path: events.append(('plugin', path)))
    monkeypatch.setattr(tus_userspacebuild, 'get_target_version', lambda: '9.6')

    @contextlib.contextmanager
    def fake_nspawn(base_dir):
        events.append(('nspawn', base_dir))
        yield _BuildContext()

    monkeypatch.setattr(tus_userspacebuild.mounting, 'NspawnActions', fake_nspawn)
    monkeypatch.setattr(tus_userspacebuild.rhsm, 'set_container_mode',
                        lambda ctx: events.append(('container_mode',)))


def _layout():
    return type('L', (), {
        'userspace_path': '/var/lib/leapp/el9userspace',
        'scratch_dir': '/var/lib/leapp/scratch',
        'mounts_dir': '/var/lib/leapp/scratch/mounts',
        'target_major': '9',
    })()


def _used_repos():
    return type('U', (), {'repos': [type('R', (), {'repoid': 'baseos'})()]})()


def test_build_happy_path(monkeypatch):
    events = []
    _patch_build_commons(monkeypatch, events)
    context = _BuildContext()

    result = tus_userspacebuild.build(context, _layout(), _Inputs(nogpgcheck=False), _used_repos())

    assert isinstance(result, TargetUserSpaceInfo)
    assert result.path == '/var/lib/leapp/el9userspace'
    assert result.scratch == '/var/lib/leapp/scratch'
    assert result.mounts == '/var/lib/leapp/scratch/mounts'
    kinds = [e[0] for e in events]
    # gpg import ran, plugin installed, container mode set
    assert 'gpg' in kinds
    assert ('plugin', '/var/lib/leapp/el9userspace') in events
    assert ('container_mode',) in kinds or 'container_mode' in kinds
    assert ('prep',) in events


def test_build_skips_gpg_when_nogpgcheck(monkeypatch):
    events = []
    _patch_build_commons(monkeypatch, events)
    context = _BuildContext()

    tus_userspacebuild.build(context, _layout(), _Inputs(nogpgcheck=True), _used_repos())

    assert 'gpg' not in [e[0] for e in events]


def test_build_cleanup_only_when_not_bootstrapping(monkeypatch):
    events = []
    _patch_build_commons(monkeypatch, events)
    monkeypatch.setattr(tus_userspacebuild.tus_rhui, 'cleanup_injected_repofiles',
                        lambda ctx, ri: events.append(('cleanup',)))
    setup = type('S', (), {'bootstrap_target_client': False})()
    rhui_info = type('RI', (), {'target_client_setup_info': setup})()
    context = _BuildContext()

    tus_userspacebuild.build(context, _layout(), _Inputs(rhui_info=rhui_info), _used_repos())

    assert ('cleanup',) in events


def test_build_no_cleanup_when_bootstrapping(monkeypatch):
    events = []
    _patch_build_commons(monkeypatch, events)
    monkeypatch.setattr(tus_userspacebuild.tus_rhui, 'cleanup_injected_repofiles',
                        lambda ctx, ri: events.append(('cleanup',)))
    setup = type('S', (), {'bootstrap_target_client': True})()
    rhui_info = type('RI', (), {'target_client_setup_info': setup})()
    context = _BuildContext()

    tus_userspacebuild.build(context, _layout(), _Inputs(rhui_info=rhui_info), _used_repos())

    assert ('cleanup',) not in events


def test_build_diagnoses_dnf_failure(monkeypatch):
    events = []
    _patch_build_commons(monkeypatch, events)

    class FailingContext(_BuildContext):
        def call(self, cmd, *a, **k):
            if cmd[:2] == ['dnf', 'install']:
                raise _cpe(stdout='more space needed on the /var')
            return {'stdout': []}

    with pytest.raises(StopActorExecutionError) as err:
        tus_userspacebuild.build(FailingContext(), _layout(), _Inputs(), _used_repos())
    assert err.value.details['link'] == tus_userspacebuild._DEDICATED_LEAPP_PARTITION_URL
