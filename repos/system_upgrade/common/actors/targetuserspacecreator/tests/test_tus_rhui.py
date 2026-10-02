import contextlib
import io

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_rhui
from leapp.libraries.stdlib import CalledProcessError
from leapp.models import (
    CopyFile,
    RHUIInfo,
    TargetRHUIPostInstallTasks,
    TargetRHUIPreInstallTasks,
    TargetRHUISetupInfo,
)


def _cpe():
    return CalledProcessError('boom', ['cmd'], {'exit_code': 1, 'stdout': '', 'stderr': ''})


def _rhui_info(bootstrap=True, enable_only=True, preinstall_copies=None, files_to_remove=None,
               postinstall_copies=None, supporting=None, src_pkgs=None, target_pkgs=None):
    setup = TargetRHUISetupInfo(
        enable_only_repoids_in_copied_files=enable_only,
        bootstrap_target_client=bootstrap,
        files_supporting_client_operation=supporting or [],
        preinstall_tasks=TargetRHUIPreInstallTasks(
            files_to_remove=files_to_remove or [],
            files_to_copy_into_overlay=preinstall_copies or [],
        ),
        postinstall_tasks=TargetRHUIPostInstallTasks(
            files_to_copy=postinstall_copies or [],
        ),
    )
    return RHUIInfo(
        provider='aws',
        src_client_pkg_names=src_pkgs if src_pkgs is not None else ['src-client'],
        target_client_pkg_names=target_pkgs if target_pkgs is not None else ['tgt-client'],
        target_client_setup_info=setup,
    )


class FakeContext(object):
    def __init__(self, repolist_stdout=None, fail_repolist=False, rpm_ql=None, dirs=None,
                 files=None, listdir=None):
        self.calls = []
        self.removed = []
        self.copied_to = []
        self.written = {}
        self._repolist_stdout = repolist_stdout or []
        self._fail_repolist = fail_repolist
        self._rpm_ql = rpm_ql or {}
        self._dirs = set(dirs or [])
        self._files = set(files or [])
        self._listdir = listdir or {}

    def full_path(self, path):
        return '/container' + path

    def call(self, cmd, *args, **kwargs):
        self.calls.append(cmd)
        if cmd[0] == 'dnf' and 'repolist' in cmd:
            if self._fail_repolist:
                raise _cpe()
            return {'stdout': self._repolist_stdout}
        if cmd[:2] == ['rpm', '-ql']:
            pkg = cmd[2]
            if pkg in self._rpm_ql:
                return {'stdout': self._rpm_ql[pkg]}
            raise _cpe()
        if cmd[:2] == ['rpm', '-qf']:
            path = cmd[2]
            if path in self._files_owned:
                return {'stdout': ['pkg']}
            raise _cpe()
        return {'stdout': []}

    _files_owned = set()

    def remove(self, path):
        self.removed.append(path)

    def copy_to(self, src, dst):
        self.copied_to.append((src, dst))

    @contextlib.contextmanager
    def open(self, path, mode='r'):
        buf = io.StringIO()
        yield buf
        self.written[path] = buf.getvalue()


# --------------------------------------------------------------------------- #
# Falsy rhui_info -> every entry point is a no-op
# --------------------------------------------------------------------------- #
def test_noop_when_rhui_info_falsy():
    context = FakeContext()
    tus_rhui.perform_client_swap(context, None, '9', '9.6', False)
    assert tus_rhui.discover_client_exposed_repoids(context, None) == set()
    tus_rhui.cleanup_injected_repofiles(context, None)
    assert context.calls == []


# --------------------------------------------------------------------------- #
# R1 - copy-target path resolution
# --------------------------------------------------------------------------- #
def test_resolve_copy_target_existing_dir(monkeypatch):
    context = FakeContext()
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: p == '/container/etc/yum.repos.d')
    copy_file = CopyFile(src='/host/my.repo', dst='/etc/yum.repos.d')
    assert tus_rhui._resolve_copy_target(context, copy_file) == '/etc/yum.repos.d/my.repo'


def test_resolve_copy_target_non_dir(monkeypatch):
    context = FakeContext()
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: False)
    copy_file = CopyFile(src='/host/my.repo', dst='/etc/yum.repos.d/target.repo')
    assert tus_rhui._resolve_copy_target(context, copy_file) == '/etc/yum.repos.d/target.repo'


# --------------------------------------------------------------------------- #
# R2 - discovery hides foreign repofiles, runs repolist, restores everything
# --------------------------------------------------------------------------- #
def test_discover_hides_and_restores(monkeypatch):
    context = FakeContext(repolist_stdout=[
        'repo id       repo name',
        'client-repo   Client Repo',
        'client-source Client Source',   # excluded (contains 'source')
        'client-debug-rpms Debug',       # excluded (contains '-debug-')
    ])
    monkeypatch.setattr(tus_rhui, '_list_repofiles', lambda ctx: ['foreign.repo', 'client.repo'])
    monkeypatch.setattr(tus_rhui, '_client_owned_repofiles', lambda ctx, ri: {'client.repo'})
    monkeypatch.setattr(tus_rhui, '_setup_copied_repofiles', lambda ctx, ri: set())

    repoids = tus_rhui.discover_client_exposed_repoids(context, _rhui_info())

    assert repoids == {'client-repo'}
    # foreign.repo hidden then restored; the mv calls bracket the repolist
    mv_calls = [c for c in context.calls if c[0] == 'mv']
    assert mv_calls == [
        ['mv', '/etc/yum.repos.d/foreign.repo', '/etc/yum.repos.d/foreign.repo.leapp-hidden'],
        ['mv', '/etc/yum.repos.d/foreign.repo.leapp-hidden', '/etc/yum.repos.d/foreign.repo'],
    ]


def test_discover_restores_even_on_repolist_failure(monkeypatch):
    context = FakeContext(fail_repolist=True)
    monkeypatch.setattr(tus_rhui, '_list_repofiles', lambda ctx: ['foreign.repo'])
    monkeypatch.setattr(tus_rhui, '_client_owned_repofiles', lambda ctx, ri: set())
    monkeypatch.setattr(tus_rhui, '_setup_copied_repofiles', lambda ctx, ri: set())

    with pytest.raises(StopActorExecutionError):
        tus_rhui.discover_client_exposed_repoids(context, _rhui_info())

    # restore still happened despite the failure
    assert ['mv', '/etc/yum.repos.d/foreign.repo.leapp-hidden', '/etc/yum.repos.d/foreign.repo'] in context.calls


def test_client_owned_empty_when_not_bootstrapping(monkeypatch):
    context = FakeContext()
    called = {'n': 0}

    def fake_owned(ctx, dirpath, pkgs=None):
        called['n'] += 1
        return ['x.repo']

    monkeypatch.setattr(tus_rhui.tus_repoaccess, '_get_files_owned_by_rpms', fake_owned)
    assert tus_rhui._client_owned_repofiles(context, _rhui_info(bootstrap=False)) == set()
    assert called['n'] == 0


# --------------------------------------------------------------------------- #
# R5 - orchestration
# --------------------------------------------------------------------------- #
def test_perform_client_swap_early_return_when_not_bootstrapping(monkeypatch):
    context = FakeContext()
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: False)
    monkeypatch.setattr(tus_rhui.os, 'makedirs', lambda p: None)
    rhui_info = _rhui_info(bootstrap=False,
                           preinstall_copies=[CopyFile(src='/h/a.repo', dst='/etc/yum.repos.d/a.repo')])

    tus_rhui.perform_client_swap(context, rhui_info, '9', '9.6', False)

    # pre-install copy happened, but no dnf shell swap
    assert ('/h/a.repo', '/etc/yum.repos.d/a.repo') in context.copied_to
    assert not any(c[0] == 'dnf' and 'shell' in c for c in context.calls)


def test_perform_client_swap_order_and_flags(monkeypatch):
    context = FakeContext(rpm_ql={'tgt-client': ['/etc/yum.repos.d/tgt.repo']})
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: False)
    rhui_info = _rhui_info(bootstrap=True, enable_only=False,
                           src_pkgs=['src-client'], target_pkgs=['tgt-client'])

    tus_rhui.perform_client_swap(context, rhui_info, '9', '9.6', True)

    # dnf shell script content: remove -> install -> run
    script = [v for k, v in context.written.items() if k.endswith('.dnfsh')][0]
    lines = [ln for ln in script.splitlines() if ln]
    assert lines == ['remove src-client', 'install tgt-client', 'run']

    dnf_shell = [c for c in context.calls if c[0] == 'dnf' and 'shell' in c][0]
    assert '--disableplugin' in dnf_shell and 'subscription-manager' in dnf_shell
    assert '--setopt=module_platform_id=platform:el9' in dnf_shell


def test_perform_client_swap_client_not_found_hard_stops(monkeypatch):
    # rpm -ql returns nothing for the target client -> hard stop
    context = FakeContext(rpm_ql={})
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: False)
    rhui_info = _rhui_info(bootstrap=True, enable_only=False)

    with pytest.raises(StopActorExecutionError):
        tus_rhui.perform_client_swap(context, rhui_info, '9', '9.6', False)


# --------------------------------------------------------------------------- #
# R6 - injected repofile cleanup
# --------------------------------------------------------------------------- #
def test_cleanup_deletes_unowned_keeps_owned(monkeypatch):
    context = FakeContext()
    # a.repo owned by an rpm -> keep; b.repo not owned -> delete
    FakeContext._files_owned = {'/etc/yum.repos.d/a.repo'}
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: False)
    monkeypatch.setattr(tus_rhui.os.path, 'isfile', lambda p: True)

    rhui_info = _rhui_info(preinstall_copies=[
        CopyFile(src='/h/a.repo', dst='/etc/yum.repos.d/a.repo'),
        CopyFile(src='/h/b.repo', dst='/etc/yum.repos.d/b.repo'),
    ])

    tus_rhui.cleanup_injected_repofiles(context, rhui_info)

    assert context.removed == ['/etc/yum.repos.d/b.repo']
    FakeContext._files_owned = set()
