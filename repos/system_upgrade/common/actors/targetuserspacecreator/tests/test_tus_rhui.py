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

_YUM = '/etc/yum.repos.d'


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


class _Repo(object):
    def __init__(self, repoid):
        self.repoid = repoid


class _RepoFile(object):
    def __init__(self, repoids):
        self.data = [_Repo(repoid) for repoid in repoids]


class FakeContext(object):
    def __init__(self, repolist_stdout='', fail_repolist=False, rpm_ql=None, owned_files=None):
        self.calls = []
        self.removed = []
        self.copied_to = []
        self.made_dirs = []
        self.written = {}
        self._repolist_stdout = repolist_stdout
        self._fail_repolist = fail_repolist
        self._rpm_ql = rpm_ql or {}        # pkg name -> list of owned file paths
        self._owned_files = set(owned_files or [])  # paths for which `rpm -qf` succeeds

    def full_path(self, path):
        return '/container' + path

    def call(self, cmd, *args, **kwargs):
        self.calls.append(cmd)
        if cmd[0] == 'dnf' and 'repolist' in cmd:
            if self._fail_repolist:
                raise _cpe()
            return {'stdout': self._repolist_stdout}
        if cmd[:2] == ['rpm', '-ql']:
            stdout = []
            for pkg in cmd[2:]:
                if pkg not in self._rpm_ql:
                    raise _cpe()
                stdout.extend(self._rpm_ql[pkg])
            return {'stdout': stdout}
        if cmd[:2] == ['rpm', '-qf']:
            if cmd[2] in self._owned_files:
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
def test_perform_client_swap_noop_when_falsy():
    context = FakeContext()
    tus_rhui.perform_client_swap(context, None, '9.6', False)
    assert context.calls == []


def test_discover_noop_when_falsy():
    context = FakeContext()
    assert tus_rhui.discover_client_exposed_repoids(context, None, '9.6') == set()
    assert context.calls == []


def test_cleanup_noop_when_falsy():
    context = FakeContext()
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


def test_resolve_copy_target_null_dst_falls_back_to_src(monkeypatch):
    context = FakeContext()
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: False)
    copy_file = CopyFile(src='/host/my.repo', dst=None)
    assert tus_rhui._resolve_copy_target(context, copy_file) == '/host/my.repo'


def test_sanitized_copy_files_iter_resolves_and_sorts(monkeypatch):
    context = FakeContext()
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: p == '/container/etc/yum.repos.d')
    copy_files = [
        CopyFile(src='/host/z.repo', dst='/etc/yum.repos.d'),   # -> /etc/yum.repos.d/z.repo
        CopyFile(src='/host/a.conf', dst=None),                 # dst empty -> src
        CopyFile(src='/host/m.repo', dst='/etc/custom.repo'),   # non-dir dst kept as-is
    ]

    result = list(tus_rhui._sanitized_copy_files_iter(context, copy_files))

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
    # copies applied sorted by destination, each with its parent dir created
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
# R4 - postinstall tasks: in-container copies via `cp`, sorted
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
    renames = []
    monkeypatch.setattr(tus_rhui.os, 'rename', lambda a, b: renames.append((a, b)))
    monkeypatch.setattr(tus_rhui, '_get_repofiles_paths',
                        lambda ctx: {_YUM + '/foreign.repo', _YUM + '/client.repo'})
    monkeypatch.setattr(tus_rhui, '_find_rhui_client_repofiles',
                        lambda ctx, pkgs, major: {_YUM + '/client.repo'})
    monkeypatch.setattr(tus_rhui, '_repofiles_copied_at_setup', lambda ctx, files: set())
    context = FakeContext(repolist_stdout='Repo-id  : client-repo\nRepo-name : Client')

    repoids = tus_rhui.discover_client_exposed_repoids(context, _rhui_info(), '9.6')

    assert repoids == {'client-repo'}
    # foreign hidden with the .path suffix, then restored; client.repo untouched
    assert (_YUM + '/foreign.repo', _YUM + '/foreign.repo.path') in renames
    assert (_YUM + '/foreign.repo.path', _YUM + '/foreign.repo') in renames
    assert all('client.repo' not in a for a, b in renames)


def test_discover_restores_even_on_repolist_failure(monkeypatch):
    renames = []
    monkeypatch.setattr(tus_rhui.os, 'rename', lambda a, b: renames.append((a, b)))
    monkeypatch.setattr(tus_rhui, '_get_repofiles_paths', lambda ctx: {_YUM + '/foreign.repo'})
    monkeypatch.setattr(tus_rhui, '_find_rhui_client_repofiles', lambda ctx, pkgs, major: set())
    monkeypatch.setattr(tus_rhui, '_repofiles_copied_at_setup', lambda ctx, files: set())
    context = FakeContext(fail_repolist=True)

    with pytest.raises(StopActorExecutionError):
        tus_rhui.discover_client_exposed_repoids(context, _rhui_info(), '9.6')

    # restore still happened despite the failure
    assert (_YUM + '/foreign.repo.path', _YUM + '/foreign.repo') in renames


def test_discover_no_client_owned_when_not_bootstrapping(monkeypatch):
    # When not bootstrapping, no repofile is treated as client-owned, so every
    # repofile is hidden during the repolist run.
    renames = []
    monkeypatch.setattr(tus_rhui.os, 'rename', lambda a, b: renames.append((a, b)))
    monkeypatch.setattr(tus_rhui, '_get_repofiles_paths', lambda ctx: {_YUM + '/any.repo'})
    monkeypatch.setattr(tus_rhui, '_repofiles_copied_at_setup', lambda ctx, files: set())

    def _should_not_be_called(*args, **kwargs):
        raise AssertionError('_find_rhui_client_repofiles must not run when not bootstrapping')

    monkeypatch.setattr(tus_rhui, '_find_rhui_client_repofiles', _should_not_be_called)
    context = FakeContext(repolist_stdout='')

    tus_rhui.discover_client_exposed_repoids(context, _rhui_info(bootstrap=False), '9.6')

    assert (_YUM + '/any.repo', _YUM + '/any.repo.path') in renames


# --------------------------------------------------------------------------- #
# _parse_repoids_from_copied_files - parse from the copied .repo *sources*
# --------------------------------------------------------------------------- #
def test_parse_repoids_from_copied_files(monkeypatch):
    repofiles = {
        '/host/a.repo': _RepoFile(['repo-a1', 'repo-a2']),
        '/host/b.repo': _RepoFile(['repo-b1']),
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
    assert dnf_shell[dnf_shell.index('--releasever') + 1] == '9.6'
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
            CopyFile(src='/h/client.repo', dst='/etc/yum.repos.d/client.repo'),    # client-owned -> keep
            CopyFile(src='/h/support.repo', dst='/etc/yum.repos.d/support.repo'),   # supporting -> keep
            CopyFile(src='/h/drop.repo', dst='/etc/yum.repos.d/drop.repo'),         # neither -> remove
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
    context = FakeContext(owned_files={'/etc/yum.repos.d/a.repo'})
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: False)
    monkeypatch.setattr(tus_rhui.os.path, 'isfile', lambda p: True)

    rhui_info = _rhui_info(preinstall_copies=[
        CopyFile(src='/h/a.repo', dst='/etc/yum.repos.d/a.repo'),
        CopyFile(src='/h/b.repo', dst='/etc/yum.repos.d/b.repo'),
    ])

    tus_rhui.cleanup_injected_repofiles(context, rhui_info)

    assert context.removed == ['/etc/yum.repos.d/b.repo']


def test_cleanup_skips_non_repo_and_missing_files(monkeypatch):
    context = FakeContext(owned_files=set())
    monkeypatch.setattr(tus_rhui.os.path, 'isdir', lambda p: False)
    # nothing is an existing file -> nothing removed even though b.repo is unowned
    monkeypatch.setattr(tus_rhui.os.path, 'isfile', lambda p: False)

    rhui_info = _rhui_info(preinstall_copies=[
        CopyFile(src='/h/b.repo', dst='/etc/yum.repos.d/b.repo'),
        CopyFile(src='/h/notrepo.conf', dst='/etc/notrepo.conf'),
    ])

    tus_rhui.cleanup_injected_repofiles(context, rhui_info)

    assert context.removed == []
