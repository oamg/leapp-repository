"""Unit tests for the tus_rhui library of the target_userspace_creator actor."""

import os

import pytest
from test_tus_mock_utils import make_cpe, make_rhui_info, MockContext

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_constants, tus_rhui
from leapp.libraries.common import repofileutils
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    CopyFile,
    RepositoryData,
    RepositoryFile,
    TargetRHUIPostInstallTasks,
    TargetRHUIPreInstallTasks
)

_SWAP_SCRIPT_PATH = '/leapp-rhui-swap.dnfsh'


def _raise_oserror(*args, **kwargs):
    """Raise an ``OSError`` to simulate a failing file operation on the context."""
    raise OSError('simulated file operation failure')


@pytest.mark.parametrize(
    ('base_dir', 'isdir_path', 'src', 'dst', 'expected'),
    [
        # dst resolves to an existing dir -> file lands at dst/basename(src).
        # isdir is True only for the full_path of dst, proving full_path is applied.
        ('/scratch', '/scratch/etc/dir', '/host/file.repo', '/etc/dir', '/etc/dir/file.repo'),
        # dst is not a dir -> used unchanged (isdir_path matches nothing).
        ('/base', None, '/host/file.repo', '/etc/target.repo', '/etc/target.repo'),
    ]
)
def test_resolve_copy_target(monkeypatch, base_dir, isdir_path, src, dst, expected):
    ctx = MockContext(base_dir=base_dir)
    monkeypatch.setattr(os.path, 'isdir', lambda p: p == isdir_path)
    assert tus_rhui._resolve_copy_target(ctx, CopyFile(src=src, dst=dst)) == expected


def test_sanitized_copy_files_iter_sorts_by_dst(monkeypatch):
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    ctx = MockContext()
    copy_files = [
        CopyFile(src='/a', dst='/z.repo'),
        CopyFile(src='/b', dst='/a.repo'),
        CopyFile(src='/c', dst='/m.repo'),
    ]
    result = list(tus_rhui._sanitized_copy_files_iter(ctx, copy_files))
    assert result == [('/b', '/a.repo'), ('/c', '/m.repo'), ('/a', '/z.repo')]


def test_run_preinstall_tasks_none(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    ctx = MockContext()
    tus_rhui._run_preinstall_tasks(ctx, None)
    assert not ctx.remove_calls
    assert not ctx.copy_to_calls


def test_run_preinstall_tasks_full(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    ctx = MockContext()
    tasks = TargetRHUIPreInstallTasks(
        files_to_remove=['/old1', '/old2'],
        files_to_copy_into_overlay=[CopyFile(src='/h/a.repo', dst='/etc/a.repo')],
    )
    tus_rhui._run_preinstall_tasks(ctx, tasks)
    assert ctx.remove_calls == ['/old1', '/old2']
    assert ctx.copy_to_calls == [('/h/a.repo', '/etc/a.repo')]
    assert ctx.makedirs_calls == [('/etc', True)]


def test_run_preinstall_tasks_remove_failure_stops(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    ctx = MockContext()
    monkeypatch.setattr(ctx, 'remove', _raise_oserror)
    tasks = TargetRHUIPreInstallTasks(files_to_remove=['/old1'], files_to_copy_into_overlay=[])
    with pytest.raises(StopActorExecutionError):
        tus_rhui._run_preinstall_tasks(ctx, tasks)


def test_run_preinstall_tasks_copy_failure_stops(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    ctx = MockContext()
    monkeypatch.setattr(ctx, 'copy_to', _raise_oserror)
    tasks = TargetRHUIPreInstallTasks(
        files_to_remove=[],
        files_to_copy_into_overlay=[CopyFile(src='/h/a.repo', dst='/etc/a.repo')],
    )
    with pytest.raises(StopActorExecutionError):
        tus_rhui._run_preinstall_tasks(ctx, tasks)


def test_run_postinstall_tasks_none(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    ctx = MockContext()
    tus_rhui._run_postinstall_tasks(ctx, None)
    assert not ctx.calls


def test_run_postinstall_tasks_full(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    ctx = MockContext()
    tasks = TargetRHUIPostInstallTasks(files_to_copy=[CopyFile(src='/s/x', dst='/d/x')])
    tus_rhui._run_postinstall_tasks(ctx, tasks)
    assert ctx.makedirs_calls == [('/d', True)]
    assert ctx.calls == [['cp', '/s/x', '/d/x']]


def test_run_postinstall_tasks_cp_failure_stops(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    ctx = MockContext(raise_on_call=make_cpe(command=['cp', '/s/x', '/d/x']))
    tasks = TargetRHUIPostInstallTasks(files_to_copy=[CopyFile(src='/s/x', dst='/d/x')])
    with pytest.raises(StopActorExecutionError):
        tus_rhui._run_postinstall_tasks(ctx, tasks)
    assert ctx.calls == [['cp', '/s/x', '/d/x']]


def test_run_postinstall_tasks_makedirs_failure_stops(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    ctx = MockContext()
    monkeypatch.setattr(ctx, 'makedirs', _raise_oserror)
    tasks = TargetRHUIPostInstallTasks(files_to_copy=[CopyFile(src='/s/x', dst='/d/x')])
    with pytest.raises(StopActorExecutionError):
        tus_rhui._run_postinstall_tasks(ctx, tasks)
    assert not ctx.calls


def test_get_repofiles_paths_no_dir(monkeypatch):
    ctx = MockContext()
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    assert tus_rhui._get_repofiles_paths(ctx) == set()


def test_get_repofiles_paths(monkeypatch):
    ctx = MockContext()
    monkeypatch.setattr(os.path, 'isdir', lambda p: True)
    monkeypatch.setattr(os, 'listdir', lambda p: ['a.repo', 'b.repo', 'notrepo.txt'])
    expected = {'/etc/yum.repos.d/a.repo', '/etc/yum.repos.d/b.repo'}
    assert tus_rhui._get_repofiles_paths(ctx) == expected


def test_repofiles_copied_at_setup(monkeypatch):
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    ctx = MockContext()
    files = [
        CopyFile(src='/h/a.repo', dst='/etc/yum.repos.d/a.repo'),
        CopyFile(src='/h/b.conf', dst='/etc/b.conf'),
    ]
    assert tus_rhui._repofiles_copied_at_setup(ctx, files) == {'/etc/yum.repos.d/a.repo'}


def test_dnf_repolist_repoids():
    stdout = [
        'Repo-id : rhel-9-baseos',
        'Repo-name : BaseOS',
        'Repo-id : rhel-9-appstream',
        'some other line',
    ]
    ctx = MockContext(call_result={'stdout': stdout})
    result = tus_rhui._dnf_repolist_repoids(ctx, '9.6')
    assert result == {'rhel-9-baseos', 'rhel-9-appstream'}
    expected_cmd = [
        'dnf', 'repolist',
        '--releasever', '9.6',
        '-v',
        '--enablerepo', '*',
        '--disablerepo', '*-source-*',
        '--disablerepo', '*-debug-*',
    ]
    assert ctx.calls == [expected_cmd]


def test_discover_client_exposed_repoids_no_rhui():
    ctx = MockContext()
    assert tus_rhui.discover_client_exposed_repoids(ctx, None, '9.6') == set()


def test_discover_client_exposed_repoids_success(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    ctx = MockContext()
    renames = []
    monkeypatch.setattr(tus_rhui.os, 'rename', lambda a, b: renames.append((a, b)))
    monkeypatch.setattr(
        tus_rhui, '_get_repofiles_paths',
        lambda c: {'/etc/yum.repos.d/client.repo', '/etc/yum.repos.d/foreign.repo'}
    )
    monkeypatch.setattr(
        tus_rhui, '_find_rhui_client_repofiles',
        lambda c, p, v: {'/etc/yum.repos.d/client.repo'}
    )
    monkeypatch.setattr(tus_rhui, '_repofiles_copied_at_setup', lambda c, f: set())
    monkeypatch.setattr(tus_rhui, '_dnf_repolist_repoids', lambda c, v: {'repoA'})
    rhui_info = make_rhui_info(bootstrap=True)
    result = tus_rhui.discover_client_exposed_repoids(ctx, rhui_info, '9.6')
    assert result == {'repoA'}
    # os.rename operates on the real filesystem path (context.full_path), not the
    # container-relative path. Only the foreign repofile is hidden and restored;
    # the client-owned repofile is never touched.
    assert ('/base/etc/yum.repos.d/foreign.repo', '/base/etc/yum.repos.d/foreign.repo.back') in renames
    assert ('/base/etc/yum.repos.d/foreign.repo.back', '/base/etc/yum.repos.d/foreign.repo') in renames


def test_discover_client_exposed_repoids_failure_reverts(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    ctx = MockContext()
    renames = []
    monkeypatch.setattr(tus_rhui.os, 'rename', lambda a, b: renames.append((a, b)))
    monkeypatch.setattr(tus_rhui, '_get_repofiles_paths', lambda c: {'/etc/yum.repos.d/foreign.repo'})
    monkeypatch.setattr(tus_rhui, '_find_rhui_client_repofiles', lambda c, p, v: set())
    monkeypatch.setattr(tus_rhui, '_repofiles_copied_at_setup', lambda c, f: set())

    def _boom(c, v):
        raise make_cpe(stderr='repolist failed')

    monkeypatch.setattr(tus_rhui, '_dnf_repolist_repoids', _boom)
    rhui_info = make_rhui_info(bootstrap=True)
    with pytest.raises(StopActorExecutionError):
        tus_rhui.discover_client_exposed_repoids(ctx, rhui_info, '9.6')
    # The finally block restores the hidden repofile even when dnf repolist fails.
    assert ('/base/etc/yum.repos.d/foreign.repo', '/base/etc/yum.repos.d/foreign.repo.back') in renames
    assert ('/base/etc/yum.repos.d/foreign.repo.back', '/base/etc/yum.repos.d/foreign.repo') in renames


def test_discover_client_exposed_repoids_no_bootstrap(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    ctx = MockContext()
    renames = []
    monkeypatch.setattr(tus_rhui.os, 'rename', lambda a, b: renames.append((a, b)))
    monkeypatch.setattr(tus_rhui, '_get_repofiles_paths', lambda c: {'/etc/yum.repos.d/client.repo'})

    def _no_client_repofiles(c, p, v):
        raise AssertionError('_find_rhui_client_repofiles must not run when not bootstrapping')

    monkeypatch.setattr(tus_rhui, '_find_rhui_client_repofiles', _no_client_repofiles)
    monkeypatch.setattr(tus_rhui, '_repofiles_copied_at_setup', lambda c, f: set())
    monkeypatch.setattr(tus_rhui, '_dnf_repolist_repoids', lambda c, v: {'repoA'})
    rhui_info = make_rhui_info(bootstrap=False)
    result = tus_rhui.discover_client_exposed_repoids(ctx, rhui_info, '9.6')
    assert result == {'repoA'}
    # With no client repofiles kept visible, the only existing repofile is foreign
    # and therefore hidden before the repolist and restored afterwards.
    assert ('/base/etc/yum.repos.d/client.repo', '/base/etc/yum.repos.d/client.repo.back') in renames
    assert ('/base/etc/yum.repos.d/client.repo.back', '/base/etc/yum.repos.d/client.repo') in renames


def test_parse_repoids_from_copied_files(monkeypatch):
    mapping = {
        '/h/a.repo': RepositoryFile(file='/h/a.repo', data=[
            RepositoryData(repoid='idA', name='idA'),
            RepositoryData(repoid='idB', name='idB'),
        ]),
        '/h/b.repo': RepositoryFile(file='/h/b.repo', data=[
            RepositoryData(repoid='idC', name='idC'),
        ]),
    }
    monkeypatch.setattr(tus_rhui.repofileutils, 'parse_repofile', lambda path: mapping[path])
    copy_files = [
        CopyFile(src='/h/a.repo', dst='/etc/a.repo'),
        CopyFile(src='/h/b.repo', dst='/etc/b.repo'),
        CopyFile(src='/h/not.conf', dst='/etc/not.conf'),
    ]
    assert tus_rhui._parse_repoids_from_copied_files(copy_files) == {'idA', 'idB', 'idC'}


def test_parse_repoids_from_copied_files_invalid(monkeypatch):
    def _raise(path):
        raise repofileutils.InvalidRepoDefinition('bad', repofile=path, repoid='x')

    monkeypatch.setattr(tus_rhui.repofileutils, 'parse_repofile', _raise)
    copy_files = [CopyFile(src='/h/a.repo', dst='/etc/a.repo')]
    with pytest.raises(StopActorExecutionError):
        tus_rhui._parse_repoids_from_copied_files(copy_files)


def test_swap_clients_success():
    ctx = MockContext()
    rhui_info = make_rhui_info(src_pkgs=['old-client'], target_pkgs=['new-client'])
    tus_rhui._swap_clients(ctx, rhui_info, '9.6', False, set())
    assert ctx.written_files[_SWAP_SCRIPT_PATH] == 'remove old-client\ninstall new-client\ntransaction run\n'
    expected_cmd = ['dnf', 'shell', '-y']
    expected_cmd += tus_constants.common_dnf_flags('9.6', False)
    expected_cmd.append(_SWAP_SCRIPT_PATH)
    assert ctx.calls == [expected_cmd]
    assert ctx.remove_calls == [_SWAP_SCRIPT_PATH]


def test_swap_clients_enable_only_no_src():
    ctx = MockContext()
    rhui_info = make_rhui_info(src_pkgs=[], target_pkgs=['new-client'])
    tus_rhui._swap_clients(ctx, rhui_info, '9.6', True, {'repoB', 'repoA'})
    assert ctx.written_files[_SWAP_SCRIPT_PATH] == 'install new-client\ntransaction run\n'
    expected_cmd = ['dnf', 'shell', '-y']
    expected_cmd += tus_constants.common_dnf_flags('9.6', True)
    expected_cmd.append('--disablerepo=*')
    expected_cmd.append('--enablerepo=repoA')
    expected_cmd.append('--enablerepo=repoB')
    expected_cmd.append(_SWAP_SCRIPT_PATH)
    assert ctx.calls == [expected_cmd]


def test_swap_clients_failure_removes_script():
    ctx = MockContext(raise_on_call=make_cpe(stderr='swap failed'))
    rhui_info = make_rhui_info(src_pkgs=['old'], target_pkgs=['new'])
    with pytest.raises(StopActorExecutionError):
        tus_rhui._swap_clients(ctx, rhui_info, '9.6', False, set())
    assert ctx.remove_calls == [_SWAP_SCRIPT_PATH]


def test_query_rpm_for_pkg_files():
    ctx = MockContext(call_result={'stdout': ['/etc/yum.repos.d/a.repo', '/usr/bin/x']})
    result = tus_rhui._query_rpm_for_pkg_files(ctx, ['pkg1', 'pkg2'])
    assert result == {'/etc/yum.repos.d/a.repo', '/usr/bin/x'}
    assert ctx.calls == [['rpm', '-ql', 'pkg1', 'pkg2']]


def test_find_rhui_client_repofiles():
    ctx = MockContext(call_result={'stdout': [
        '/etc/yum.repos.d/client.repo',
        '/etc/yum.repos.d/notrepo.conf',
        '/usr/share/other.repo',
    ]})
    assert tus_rhui._find_rhui_client_repofiles(ctx, ['client'], '9') == {'/etc/yum.repos.d/client.repo'}


def test_find_rhui_client_repofiles_error():
    ctx = MockContext(raise_on_call=make_cpe())
    with pytest.raises(StopActorExecutionError):
        tus_rhui._find_rhui_client_repofiles(ctx, ['client'], '9')


def test_find_rhui_client_files():
    ctx = MockContext(call_result={'stdout': ['/a', '/b']})
    assert tus_rhui._find_rhui_client_files(ctx, ['c'], '9') == {'/a', '/b'}


def test_find_rhui_client_files_error(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    ctx = MockContext(raise_on_call=make_cpe())
    with pytest.raises(StopActorExecutionError):
        tus_rhui._find_rhui_client_files(ctx, ['c'], '9')


def test_remove_nonclient_injected_files(monkeypatch):
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    ctx = MockContext()
    copies = [
        CopyFile(src='/h/client.repo', dst='/etc/client.repo'),
        CopyFile(src='/h/support.cfg', dst='/etc/support.cfg'),
        CopyFile(src='/h/junk.repo', dst='/etc/junk.repo'),
    ]
    rhui_info = make_rhui_info(preinstall_copies=copies, supporting=['/h/support.cfg'])
    tus_rhui._remove_nonclient_injected_files(ctx, rhui_info, {'/etc/client.repo'})
    assert ctx.remove_calls == ['/etc/junk.repo']


def test_perform_client_swap_no_rhui():
    ctx = MockContext()
    tus_rhui.perform_client_swap(ctx, None, '9.6', False)
    assert not ctx.calls


def test_perform_client_swap_no_bootstrap(monkeypatch):
    calls = []
    monkeypatch.setattr(tus_rhui, '_run_preinstall_tasks', lambda c, t: calls.append('preinstall'))
    monkeypatch.setattr(tus_rhui, '_swap_clients', lambda *a: calls.append('swap'))
    ctx = MockContext()
    rhui_info = make_rhui_info(bootstrap=False)
    tus_rhui.perform_client_swap(ctx, rhui_info, '9.6', False)
    assert calls == ['preinstall']


def test_perform_client_swap_full(monkeypatch):
    calls = []
    swapped = {}
    monkeypatch.setattr(tus_rhui, '_run_preinstall_tasks', lambda c, t: calls.append('preinstall'))
    monkeypatch.setattr(tus_rhui, '_parse_repoids_from_copied_files', lambda f: {'repoX'})

    def _fake_swap(c, info, ver, skip, enable):
        calls.append('swap')
        swapped['enable'] = enable

    monkeypatch.setattr(tus_rhui, '_swap_clients', _fake_swap)
    monkeypatch.setattr(tus_rhui, '_run_postinstall_tasks', lambda c, t: calls.append('postinstall'))
    monkeypatch.setattr(tus_rhui, '_find_rhui_client_files', lambda c, p, v: {'/f'})
    monkeypatch.setattr(tus_rhui, '_remove_nonclient_injected_files', lambda c, info, cf: calls.append('remove'))
    ctx = MockContext()
    copies = [CopyFile(src='/h/a.repo', dst='/etc/a.repo')]
    rhui_info = make_rhui_info(bootstrap=True, enable_only=True, preinstall_copies=copies)
    tus_rhui.perform_client_swap(ctx, rhui_info, '9.6', False)
    assert calls == ['preinstall', 'swap', 'postinstall', 'remove']
    assert swapped['enable'] == {'repoX'}


@pytest.mark.parametrize(
    ('enable_only', 'preinstall_copies'),
    [
        # Toggle off (even though copies exist) -> parsing skipped.
        pytest.param(False, [CopyFile(src='/h/a.repo', dst='/etc/a.repo')], id='enable-flag-off'),
        # Toggle on but no copies to parse -> parsing skipped.
        pytest.param(True, [], id='no-preinstall-copies'),
    ]
)
def test_perform_client_swap_enable_repoids_stays_empty(monkeypatch, enable_only, preinstall_copies):
    """
    ``enable_only_repoids`` stays empty unless the toggle is set AND preinstall
    copies exist. In either single-condition case the copied-files repoid parsing
    is skipped and the swap is run without restricting the enabled repos.
    """
    swapped = {}
    monkeypatch.setattr(tus_rhui, '_run_preinstall_tasks', lambda c, t: None)

    def _no_parse(f):
        raise AssertionError('_parse_repoids_from_copied_files must not be called')

    monkeypatch.setattr(tus_rhui, '_parse_repoids_from_copied_files', _no_parse)

    def _fake_swap(c, info, ver, skip, enable):
        swapped['enable'] = enable

    monkeypatch.setattr(tus_rhui, '_swap_clients', _fake_swap)
    monkeypatch.setattr(tus_rhui, '_run_postinstall_tasks', lambda c, t: None)
    monkeypatch.setattr(tus_rhui, '_find_rhui_client_files', lambda c, p, v: set())
    monkeypatch.setattr(tus_rhui, '_remove_nonclient_injected_files', lambda c, info, cf: None)
    ctx = MockContext()
    rhui_info = make_rhui_info(bootstrap=True, enable_only=enable_only, preinstall_copies=preinstall_copies)
    tus_rhui.perform_client_swap(ctx, rhui_info, '9.6', False)
    assert swapped['enable'] == set()


def test_cleanup_injected_repofiles_no_rhui():
    ctx = MockContext()
    tus_rhui.cleanup_injected_repofiles(ctx, None)
    assert not ctx.remove_calls


def test_cleanup_injected_repofiles(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    monkeypatch.setattr(os.path, 'isfile', lambda p: True)
    ctx = MockContext()

    def _fake_call(cmd, split=False, callback_raw=None):
        ctx.calls.append(cmd)
        if cmd == ['rpm', '-qf', '/etc/b.repo']:
            raise make_cpe()
        return {'stdout': 'pkg'}

    ctx.call = _fake_call
    copies = [
        CopyFile(src='/h/a.repo', dst='/etc/a.repo'),
        CopyFile(src='/h/b.repo', dst='/etc/b.repo'),
        CopyFile(src='/h/c.conf', dst='/etc/c.conf'),
    ]
    rhui_info = make_rhui_info(preinstall_copies=copies)
    tus_rhui.cleanup_injected_repofiles(ctx, rhui_info)
    assert ctx.remove_calls == ['/etc/b.repo']
