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


class _FakeRepoEntry(object):
    def __init__(self, repoid):
        self.repoid = repoid


class _FakeRepoFile(object):
    def __init__(self, repoids):
        self.data = [_FakeRepoEntry(repoid) for repoid in repoids]


class FakeContext(object):
    def __init__(self, repolist_stdout=None, fail_repolist=False, rpm_ql=None, files_owned=None):
        self.calls = []
        self.removed = []
        self.copied_to = []
        self.made_dirs = []
        self.written = {}
        self._repolist_stdout = repolist_stdout or []
        self._fail_repolist = fail_repolist
        self._rpm_ql = rpm_ql or {}
        self._files_owned = set(files_owned or [])

    def full_path(self, path):
        return '/container' + path

    def call(self, cmd, *args, **kwargs):
        self.calls.append(cmd)
        if cmd[0] == 'dnf' and 'repolist' in cmd:
            if self._fail_repolist:
                raise _cpe()
            return {'stdout': self._repolist_stdout}
        if cmd[:2] == ['rpm', '-ql']:
            # single `rpm -ql pkg1 pkg2 ...` call: fails if any pkg is missing
            stdout = []
            for pkg in cmd[2:]:
                if pkg not in self._rpm_ql:
                    raise _cpe()
                stdout.extend(self._rpm_ql[pkg])
            return {'stdout': stdout}
        if cmd[:2] == ['rpm', '-qf']:
            if cmd[2] in self._files_owned:
                return {'stdout': ['pkg']}
            raise _cpe()
        return {'stdout': []}

    def makedirs(self, path, mode=0o777, exists_ok=True):
        self.made_dirs.append(path)

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
    tus_rhui.perform_client_swap(context, None, '9.6', False)
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
# _sanitized_copy_files_iter - resolves dst, falls back to src, sorts by dst
# --------------------------------------------------------------------------- #
def test_sanitized_copy_files_iter_resolves_and_sorts(monkeypatch):
    context = FakeContext()
    # only /etc/yum.repos.d is an existing dir inside the container
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: p == '/container/etc/yum.repos.d')
    copy_files = [
        CopyFile(src='/host/z.repo', dst='/etc/yum.repos.d'),   # -> /etc/yum.repos.d/z.repo
        CopyFile(src='/host/a.conf', dst=None),                 # dst empty -> src
        CopyFile(src='/host/m.repo', dst='/etc/custom.repo'),   # non-dir dst kept as-is
    ]

    result = list(tus_rhui._sanitized_copy_files_iter(context, copy_files))

    # yields (src, resolved_dst) ordered by resolved_dst
    assert result == [
        ('/host/m.repo', '/etc/custom.repo'),
        ('/host/z.repo', '/etc/yum.repos.d/z.repo'),
        ('/host/a.conf', '/host/a.conf'),
    ]


# --------------------------------------------------------------------------- #
# R3 - preinstall tasks: removals first, then sorted host->container copies
# --------------------------------------------------------------------------- #
def test_run_preinstall_tasks_removes_then_copies(monkeypatch):
    context = FakeContext()
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: False)
    preinstall = TargetRHUIPreInstallTasks(
        files_to_remove=['/etc/old.repo'],
        files_to_copy_into_overlay=[
            CopyFile(src='/host/b.repo', dst='/etc/yum.repos.d/b.repo'),
            CopyFile(src='/host/a.repo', dst='/etc/yum.repos.d/a.repo'),
        ],
    )

    tus_rhui._run_preinstall_tasks(context, preinstall)

    assert context.removed == ['/etc/old.repo']
    # copies are applied sorted by destination, each with its parent dir created
    assert context.copied_to == [
        ('/host/a.repo', '/etc/yum.repos.d/a.repo'),
        ('/host/b.repo', '/etc/yum.repos.d/b.repo'),
    ]
    assert context.made_dirs == ['/etc/yum.repos.d', '/etc/yum.repos.d']


def test_run_preinstall_tasks_noop_when_empty():
    context = FakeContext()
    tus_rhui._run_preinstall_tasks(context, None)
    assert context.calls == []
    assert context.removed == []
    assert context.copied_to == []


# --------------------------------------------------------------------------- #
# R4 - postinstall tasks: in-container copies via `cp` (no -a), sorted
# --------------------------------------------------------------------------- #
def test_run_postinstall_tasks_uses_cp_inside_container(monkeypatch):
    context = FakeContext()
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: False)
    postinstall = TargetRHUIPostInstallTasks(
        files_to_copy=[
            CopyFile(src='/in/b', dst='/out/b'),
            CopyFile(src='/in/a', dst='/out/a'),
        ],
    )

    tus_rhui._run_postinstall_tasks(context, postinstall)

    cp_calls = [c for c in context.calls if c[0] == 'cp']
    assert cp_calls == [['cp', '/in/a', '/out/a'], ['cp', '/in/b', '/out/b']]
    assert context.made_dirs == ['/out', '/out']


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
# _parse_repoids_from_copied_files - parse from the copied .repo *sources*
# --------------------------------------------------------------------------- #
def test_parse_repoids_from_copied_files(monkeypatch):
    repofiles = {
        '/host/a.repo': _FakeRepoFile(['repo-a1', 'repo-a2']),
        '/host/b.repo': _FakeRepoFile(['repo-b1']),
    }
    monkeypatch.setattr(tus_rhui.repofileutils, 'parse_repofile', lambda path: repofiles[path])
    copy_files = [
        CopyFile(src='/host/a.repo', dst='/etc/yum.repos.d/a.repo'),
        CopyFile(src='/host/b.repo', dst='/etc/yum.repos.d/b.repo'),
        CopyFile(src='/host/not-a-repo.conf', dst='/etc/x.conf'),  # skipped: no .repo suffix
    ]

    assert tus_rhui._parse_repoids_from_copied_files(copy_files) == {'repo-a1', 'repo-a2', 'repo-b1'}


def test_parse_repoids_invalid_repofile_hard_stops(monkeypatch):
    def fake_parse(path):
        raise tus_rhui.repofileutils.InvalidRepoDefinition('bad', repofile=path, repoid='x')

    monkeypatch.setattr(tus_rhui.repofileutils, 'parse_repofile', fake_parse)

    with pytest.raises(StopActorExecutionError):
        tus_rhui._parse_repoids_from_copied_files([CopyFile(src='/host/a.repo', dst=None)])


# --------------------------------------------------------------------------- #
# R5 - orchestration
# --------------------------------------------------------------------------- #
def test_perform_client_swap_early_return_when_not_bootstrapping(monkeypatch):
    context = FakeContext()
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: False)
    rhui_info = _rhui_info(bootstrap=False,
                           preinstall_copies=[CopyFile(src='/h/a.repo', dst='/etc/yum.repos.d/a.repo')])

    tus_rhui.perform_client_swap(context, rhui_info, '9.6', False)

    # pre-install copy happened, but no dnf shell swap
    assert ('/h/a.repo', '/etc/yum.repos.d/a.repo') in context.copied_to
    assert not any(c[0] == 'dnf' and 'shell' in c for c in context.calls)


def test_perform_client_swap_order_and_flags(monkeypatch):
    context = FakeContext(rpm_ql={'tgt-client': ['/etc/yum.repos.d/tgt.repo']})
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: False)
    rhui_info = _rhui_info(bootstrap=True, enable_only=False,
                           src_pkgs=['src-client'], target_pkgs=['tgt-client'])

    tus_rhui.perform_client_swap(context, rhui_info, '9.6', True)

    # dnf shell script content: remove -> install -> transaction run
    script = [v for k, v in context.written.items() if k.endswith('.dnfsh')][0]
    lines = [ln for ln in script.splitlines() if ln]
    assert lines == ['remove src-client', 'install tgt-client', 'transaction run']

    dnf_shell = [c for c in context.calls if c[0] == 'dnf' and 'shell' in c][0]
    assert '--disableplugin' in dnf_shell and 'subscription-manager' in dnf_shell
    assert '--setopt=module_platform_id=platform:el9' in dnf_shell
    assert '--releasever' in dnf_shell and '9.6' in dnf_shell
    # swap transaction script is cleaned up afterwards
    assert '/leapp-rhui-swap.dnfsh' in context.removed


def test_perform_client_swap_enable_only_repoids(monkeypatch):
    context = FakeContext(rpm_ql={'tgt-client': ['/etc/yum.repos.d/tgt.repo']})
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: False)
    monkeypatch.setattr(tus_rhui, '_parse_repoids_from_copied_files',
                        lambda copy_files: {'repo-b', 'repo-a'})
    rhui_info = _rhui_info(bootstrap=True, enable_only=True,
                           preinstall_copies=[CopyFile(src='/h/a.repo', dst='/etc/yum.repos.d/a.repo')])

    tus_rhui.perform_client_swap(context, rhui_info, '9.6', False)

    dnf_shell = [c for c in context.calls if c[0] == 'dnf' and 'shell' in c][0]
    assert '--disablerepo=*' in dnf_shell
    # repoids enabled in sorted order
    assert dnf_shell.index('--enablerepo=repo-a') < dnf_shell.index('--enablerepo=repo-b')


def test_perform_client_swap_client_not_found_hard_stops(monkeypatch):
    # rpm -ql returns nothing for the target client -> hard stop
    context = FakeContext(rpm_ql={})
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: False)
    rhui_info = _rhui_info(bootstrap=True, enable_only=False)

    with pytest.raises(StopActorExecutionError):
        tus_rhui.perform_client_swap(context, rhui_info, '9.6', False)


def test_remove_nonclient_injected_files(monkeypatch):
    context = FakeContext()
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: False)
    rhui_info = _rhui_info(
        bootstrap=True,
        supporting=['/h/support.repo'],
        preinstall_copies=[
            CopyFile(src='/h/client.repo', dst='/etc/yum.repos.d/client.repo'),   # client-owned -> keep
            CopyFile(src='/h/support.repo', dst='/etc/yum.repos.d/support.repo'),  # supporting -> keep
            CopyFile(src='/h/drop.repo', dst='/etc/yum.repos.d/drop.repo'),        # neither -> remove
        ],
    )
    client_files = {'/etc/yum.repos.d/client.repo'}

    tus_rhui._remove_nonclient_injected_files(context, rhui_info, client_files)

    assert context.removed == ['/etc/yum.repos.d/drop.repo']


# --------------------------------------------------------------------------- #
# R6 - injected repofile cleanup
# --------------------------------------------------------------------------- #
def test_cleanup_deletes_unowned_keeps_owned(monkeypatch):
    # a.repo owned by an rpm -> keep; b.repo not owned -> delete
    context = FakeContext(files_owned={'/etc/yum.repos.d/a.repo'})
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: False)
    monkeypatch.setattr(tus_rhui.os.path, 'isfile', lambda p: True)

    rhui_info = _rhui_info(preinstall_copies=[
        CopyFile(src='/h/a.repo', dst='/etc/yum.repos.d/a.repo'),
        CopyFile(src='/h/b.repo', dst='/etc/yum.repos.d/b.repo'),
    ])

    tus_rhui.cleanup_injected_repofiles(context, rhui_info)

    assert context.removed == ['/etc/yum.repos.d/b.repo']
