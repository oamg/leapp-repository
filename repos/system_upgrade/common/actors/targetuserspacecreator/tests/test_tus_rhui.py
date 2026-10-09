"""Unit tests for the tus_rhui library of the target_userspace_creator actor."""

import os

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_constants, tus_rhui
from leapp.libraries.common import repofileutils
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import CopyFile, RHUIInfo, TargetRHUIPostInstallTasks, TargetRHUIPreInstallTasks, TargetRHUISetupInfo

_SWAP_SCRIPT_PATH = '/leapp-rhui-swap.dnfsh'


class _MockOpen:
    def __init__(self, ctx, path, mode):
        self.ctx = ctx
        self.path = path
        self.mode = mode
        self._chunks = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.ctx.written[self.path] = ''.join(self._chunks)
        return False

    def write(self, data):
        self._chunks.append(data)


class MockContext:
    def __init__(self, base_dir='/scratch', call_result=None, raise_on_call=None):
        self.base_dir = base_dir
        self.call_result = call_result
        self.raise_on_call = raise_on_call
        self.calls = []
        self.removed = []
        self.copied = []
        self.makedirs_calls = []
        self.written = {}

    def full_path(self, path):
        return os.path.join(self.base_dir, path.lstrip('/'))

    def call(self, cmd, split=False, callback_raw=None):
        self.calls.append(cmd)
        if self.raise_on_call:
            raise self.raise_on_call
        return self.call_result

    def remove(self, path):
        self.removed.append(path)

    def copy_to(self, src, dst):
        self.copied.append((src, dst))

    def makedirs(self, path, exists_ok=False):
        self.makedirs_calls.append((path, exists_ok))

    def open(self, path, mode):
        return _MockOpen(self, path, mode)


class logger_with_critical(logger_mocked):
    def __init__(self):
        super().__init__()
        self.critmsg = []

    def critical(self, *args, **kwargs):
        self.critmsg.extend(args)


class MockRepofileEntry:
    def __init__(self, repoid):
        self.repoid = repoid


class MockRepofileContents:
    def __init__(self, data):
        self.data = data


def _make_cpe(stderr='some error'):
    return CalledProcessError(
        'Command failed',
        ['some', 'cmd'],
        {'stdout': 'out', 'stderr': stderr, 'exit_code': 1}
    )


def _make_setup_info(bootstrap=True, enable_only=True, preinstall_copies=None,
                     files_to_remove=None, postinstall_copies=None, supporting=None):
    preinstall = TargetRHUIPreInstallTasks(
        files_to_remove=files_to_remove or [],
        files_to_copy_into_overlay=preinstall_copies or [],
    )
    postinstall = TargetRHUIPostInstallTasks(files_to_copy=postinstall_copies or [])
    return TargetRHUISetupInfo(
        enable_only_repoids_in_copied_files=enable_only,
        preinstall_tasks=preinstall,
        postinstall_tasks=postinstall,
        files_supporting_client_operation=supporting or [],
        bootstrap_target_client=bootstrap,
    )


def _make_rhui_info(bootstrap=True, enable_only=True, preinstall_copies=None,
                    src_pkgs=None, target_pkgs=None, files_to_remove=None,
                    postinstall_copies=None, supporting=None):
    setup = _make_setup_info(
        bootstrap=bootstrap,
        enable_only=enable_only,
        preinstall_copies=preinstall_copies,
        files_to_remove=files_to_remove,
        postinstall_copies=postinstall_copies,
        supporting=supporting,
    )
    return RHUIInfo(
        provider='aws',
        src_client_pkg_names=src_pkgs if src_pkgs is not None else ['src-client'],
        target_client_pkg_names=target_pkgs if target_pkgs is not None else ['target-client'],
        target_client_setup_info=setup,
    )


@pytest.mark.parametrize(
    ('src', 'dst', 'expected'),
    [
        ('/src', '/dst', '/dst'),
        ('/src', None, '/src'),
        ('/src', '', '/src'),
    ]
)
def test_copy_file_dst(src, dst, expected):
    assert tus_rhui._copy_file_dst(CopyFile(src=src, dst=dst)) == expected


def test_resolve_copy_target_dir(monkeypatch):
    ctx = MockContext(base_dir='/scratch')
    monkeypatch.setattr(os.path, 'isdir', lambda p: p == '/scratch/etc/dir')
    cfile = CopyFile(src='/host/file.repo', dst='/etc/dir')
    assert tus_rhui._resolve_copy_target(ctx, cfile) == '/etc/dir/file.repo'


def test_resolve_copy_target_not_dir(monkeypatch):
    ctx = MockContext()
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    cfile = CopyFile(src='/host/file.repo', dst='/etc/target.repo')
    assert tus_rhui._resolve_copy_target(ctx, cfile) == '/etc/target.repo'


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
    assert not ctx.removed
    assert not ctx.copied


def test_run_preinstall_tasks_full(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    ctx = MockContext()
    tasks = TargetRHUIPreInstallTasks(
        files_to_remove=['/old1', '/old2'],
        files_to_copy_into_overlay=[CopyFile(src='/h/a.repo', dst='/etc/a.repo')],
    )
    tus_rhui._run_preinstall_tasks(ctx, tasks)
    assert ctx.removed == ['/old1', '/old2']
    assert ctx.copied == [('/h/a.repo', '/etc/a.repo')]
    assert ctx.makedirs_calls == [('/etc', True)]


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
    stdout = (
        'Repo-id : rhel-9-baseos\n'
        'Repo-name : BaseOS\n'
        'Repo-id : rhel-9-appstream\n'
        'some other line\n'
    )
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
    rhui_info = _make_rhui_info(bootstrap=True)
    result = tus_rhui.discover_client_exposed_repoids(ctx, rhui_info, '9.6')
    assert result == {'repoA'}
    assert ('/etc/yum.repos.d/foreign.repo', '/etc/yum.repos.d/foreign.repo.path') in renames
    assert ('/etc/yum.repos.d/foreign.repo.path', '/etc/yum.repos.d/foreign.repo') in renames


def test_discover_client_exposed_repoids_failure_reverts(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    ctx = MockContext()
    renames = []
    monkeypatch.setattr(tus_rhui.os, 'rename', lambda a, b: renames.append((a, b)))
    monkeypatch.setattr(tus_rhui, '_get_repofiles_paths', lambda c: {'/etc/yum.repos.d/foreign.repo'})
    monkeypatch.setattr(tus_rhui, '_find_rhui_client_repofiles', lambda c, p, v: set())
    monkeypatch.setattr(tus_rhui, '_repofiles_copied_at_setup', lambda c, f: set())

    def _boom(c, v):
        raise _make_cpe('repolist failed')

    monkeypatch.setattr(tus_rhui, '_dnf_repolist_repoids', _boom)
    rhui_info = _make_rhui_info(bootstrap=True)
    with pytest.raises(StopActorExecutionError):
        tus_rhui.discover_client_exposed_repoids(ctx, rhui_info, '9.6')
    assert ('/etc/yum.repos.d/foreign.repo.path', '/etc/yum.repos.d/foreign.repo') in renames


def test_parse_repoids_from_copied_files(monkeypatch):
    mapping = {
        '/h/a.repo': MockRepofileContents([MockRepofileEntry('idA'), MockRepofileEntry('idB')]),
        '/h/b.repo': MockRepofileContents([MockRepofileEntry('idC')]),
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
    rhui_info = _make_rhui_info(src_pkgs=['old-client'], target_pkgs=['new-client'])
    tus_rhui._swap_clients(ctx, rhui_info, '9.6', False, set())
    assert ctx.written[_SWAP_SCRIPT_PATH] == 'remove old-client\ninstall new-client\ntransaction run\n'
    expected_cmd = ['dnf', 'shell', '-y']
    expected_cmd += tus_constants.common_dnf_flags('9.6', False)
    expected_cmd.append(_SWAP_SCRIPT_PATH)
    assert ctx.calls == [expected_cmd]
    assert ctx.removed == [_SWAP_SCRIPT_PATH]


def test_swap_clients_enable_only_no_src():
    ctx = MockContext()
    rhui_info = _make_rhui_info(src_pkgs=[], target_pkgs=['new-client'])
    tus_rhui._swap_clients(ctx, rhui_info, '9.6', True, {'repoB', 'repoA'})
    assert ctx.written[_SWAP_SCRIPT_PATH] == 'install new-client\ntransaction run\n'
    expected_cmd = ['dnf', 'shell', '-y']
    expected_cmd += tus_constants.common_dnf_flags('9.6', True)
    expected_cmd.append('--disablerepo=*')
    expected_cmd.append('--enablerepo=repoA')
    expected_cmd.append('--enablerepo=repoB')
    expected_cmd.append(_SWAP_SCRIPT_PATH)
    assert ctx.calls == [expected_cmd]


def test_swap_clients_failure_removes_script():
    ctx = MockContext(raise_on_call=_make_cpe('swap failed'))
    rhui_info = _make_rhui_info(src_pkgs=['old'], target_pkgs=['new'])
    with pytest.raises(StopActorExecutionError):
        tus_rhui._swap_clients(ctx, rhui_info, '9.6', False, set())
    assert ctx.removed == [_SWAP_SCRIPT_PATH]


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
    ctx = MockContext(raise_on_call=_make_cpe())
    with pytest.raises(StopActorExecutionError):
        tus_rhui._find_rhui_client_repofiles(ctx, ['client'], '9')


def test_find_rhui_client_files():
    ctx = MockContext(call_result={'stdout': ['/a', '/b']})
    assert tus_rhui._find_rhui_client_files(ctx, ['c'], '9') == {'/a', '/b'}


def test_find_rhui_client_files_error(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_with_critical())
    ctx = MockContext(raise_on_call=_make_cpe())
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
    rhui_info = _make_rhui_info(preinstall_copies=copies, supporting=['/h/support.cfg'])
    tus_rhui._remove_nonclient_injected_files(ctx, rhui_info, {'/etc/client.repo'})
    assert ctx.removed == ['/etc/junk.repo']


def test_perform_client_swap_no_rhui():
    ctx = MockContext()
    tus_rhui.perform_client_swap(ctx, None, '9.6', False)
    assert not ctx.calls


def test_perform_client_swap_no_bootstrap(monkeypatch):
    calls = []
    monkeypatch.setattr(tus_rhui, '_run_preinstall_tasks', lambda c, t: calls.append('preinstall'))
    monkeypatch.setattr(tus_rhui, '_swap_clients', lambda *a: calls.append('swap'))
    ctx = MockContext()
    rhui_info = _make_rhui_info(bootstrap=False)
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
    rhui_info = _make_rhui_info(bootstrap=True, enable_only=True, preinstall_copies=copies)
    tus_rhui.perform_client_swap(ctx, rhui_info, '9.6', False)
    assert calls == ['preinstall', 'swap', 'postinstall', 'remove']
    assert swapped['enable'] == {'repoX'}


def test_perform_client_swap_no_enable_only(monkeypatch):
    swapped = {}
    monkeypatch.setattr(tus_rhui, '_run_preinstall_tasks', lambda c, t: None)

    def _no_parse(f):
        raise AssertionError('_parse_repoids_from_copied_files should not be called')

    monkeypatch.setattr(tus_rhui, '_parse_repoids_from_copied_files', _no_parse)

    def _fake_swap(c, info, ver, skip, enable):
        swapped['enable'] = enable

    monkeypatch.setattr(tus_rhui, '_swap_clients', _fake_swap)
    monkeypatch.setattr(tus_rhui, '_run_postinstall_tasks', lambda c, t: None)
    monkeypatch.setattr(tus_rhui, '_find_rhui_client_files', lambda c, p, v: set())
    monkeypatch.setattr(tus_rhui, '_remove_nonclient_injected_files', lambda c, info, cf: None)
    ctx = MockContext()
    copies = [CopyFile(src='/h/a.repo', dst='/etc/a.repo')]
    rhui_info = _make_rhui_info(bootstrap=True, enable_only=False, preinstall_copies=copies)
    tus_rhui.perform_client_swap(ctx, rhui_info, '9.6', False)
    assert swapped['enable'] == set()


def test_cleanup_injected_repofiles_no_rhui():
    ctx = MockContext()
    tus_rhui.cleanup_injected_repofiles(ctx, None)
    assert not ctx.removed


def test_cleanup_injected_repofiles(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    monkeypatch.setattr(os.path, 'isfile', lambda p: True)
    ctx = MockContext()

    def _fake_call(cmd, split=False, callback_raw=None):
        ctx.calls.append(cmd)
        if cmd == ['rpm', '-qf', '/etc/b.repo']:
            raise _make_cpe()
        return {'stdout': 'pkg'}

    ctx.call = _fake_call
    copies = [
        CopyFile(src='/h/a.repo', dst='/etc/a.repo'),
        CopyFile(src='/h/b.repo', dst='/etc/b.repo'),
        CopyFile(src='/h/c.conf', dst='/etc/c.conf'),
    ]
    rhui_info = _make_rhui_info(preinstall_copies=copies)
    tus_rhui.cleanup_injected_repofiles(ctx, rhui_info)
    assert ctx.removed == ['/etc/b.repo']
