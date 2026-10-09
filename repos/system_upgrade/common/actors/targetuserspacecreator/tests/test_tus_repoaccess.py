import os

import pytest

from leapp.libraries.actor import tus_repoaccess
from leapp.libraries.actor.tus_repoaccess import BrokenSymlinkError
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError


def _make_cpe():
    return CalledProcessError(
        'Command failed',
        ['rpm', '-qf', 'somefile'],
        {'stdout': '', 'stderr': 'error', 'exit_code': 1}
    )


class MockContext:
    """Minimal stand-in for mounting.IsolatedActions used by the library."""

    def __init__(self, base_dir='/base', rpm_owners=None, full_paths=None):
        self.base_dir = base_dir
        # Map of path passed to context.call(['rpm', '-qf', path]) -> stdout string.
        # Any path not present raises CalledProcessError (not owned by an rpm).
        self.rpm_owners = rpm_owners or {}
        # Optional explicit mapping for full_path; otherwise base_dir + path.
        self.full_paths = full_paths or {}
        self.calls = []
        self.copytree_from_calls = []

    def full_path(self, path):
        if path in self.full_paths:
            return self.full_paths[path]
        return os.path.join(self.base_dir, path.lstrip('/'))

    def call(self, cmd, split=False):
        self.calls.append(cmd)
        if cmd[:2] == ['rpm', '-qf']:
            queried = cmd[2]
            if queried not in self.rpm_owners:
                raise _make_cpe()
            return {'stdout': self.rpm_owners[queried]}
        return {'stdout': ''}

    def copytree_from(self, src, dst):
        self.copytree_from_calls.append((src, dst))


class RunSpy:
    """Records all calls to the module-level run() helper."""

    def __init__(self):
        self.calls = []

    def __call__(self, cmd, *args, **kwargs):
        self.calls.append(cmd)


class MockNspawnActions:
    """Context-manager replacement for mounting.NspawnActions."""

    def __init__(self, base_dir=None):
        self.base_dir = base_dir

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


# ---------------------------------------------------------------------------
# _get_files_owned_by_rpms
# ---------------------------------------------------------------------------
def test_get_files_owned_by_rpms_non_recursive(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(tus_repoaccess.os, 'listdir', lambda _: ['owned.repo', 'orphan.repo'])
    context = MockContext(rpm_owners={'/etc/yum.repos.d/owned.repo': 'some-rpm-1.0-1.noarch'})

    result = tus_repoaccess._get_files_owned_by_rpms(context, '/etc/yum.repos.d')

    assert result == ['owned.repo']


def test_get_files_owned_by_rpms_pkgs_filter(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(tus_repoaccess.os, 'listdir', lambda _: ['match.repo', 'other.repo'])
    context = MockContext(rpm_owners={
        '/etc/yum.repos.d/match.repo': 'wanted-pkg-1.0-1.noarch',
        '/etc/yum.repos.d/other.repo': 'different-2.0-1.noarch',
    })

    result = tus_repoaccess._get_files_owned_by_rpms(
        context, '/etc/yum.repos.d', pkgs=['wanted-pkg']
    )

    assert result == ['match.repo']


def test_get_files_owned_by_rpms_recursive_skips_directory_hash(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    searchdir = '/base/etc/pki'
    walk_result = [
        (searchdir, ['subdir', 'directory-hash'], ['a.crt']),
        (os.path.join(searchdir, 'subdir'), [], ['b.crt']),
        (os.path.join(searchdir, 'directory-hash'), [], ['skip-me.crt']),
    ]
    monkeypatch.setattr(tus_repoaccess.os, 'walk', lambda _: walk_result)

    owners = {
        '/etc/pki/a.crt': 'rpm-a',
        '/etc/pki/subdir/b.crt': 'rpm-b',
    }
    context = MockContext(rpm_owners=owners, full_paths={'/etc/pki': searchdir})

    result = tus_repoaccess._get_files_owned_by_rpms(
        context, '/etc/pki', recursive=True
    )

    assert result == ['a.crt', os.path.join('subdir', 'b.crt')]
    # The file under the directory-hash tree must never be queried at all.
    queried = [cmd[2] for cmd in context.calls]
    assert '/etc/pki/directory-hash/skip-me.crt' not in queried


# ---------------------------------------------------------------------------
# _mkdir_with_copied_mode
# ---------------------------------------------------------------------------
def test_mkdir_with_copied_mode(monkeypatch):
    run_spy = RunSpy()
    monkeypatch.setattr(tus_repoaccess, 'run', run_spy)

    tus_repoaccess._mkdir_with_copied_mode('/target/dir', '/source/ref')

    assert run_spy.calls == [
        ['mkdir', '-m', '0', '-p', '/target/dir'],
        ['chmod', '--reference=/source/ref', '/target/dir'],
    ]


# ---------------------------------------------------------------------------
# _refresh_ca_trust
# ---------------------------------------------------------------------------
def test_refresh_ca_trust(monkeypatch):
    run_spy = RunSpy()
    monkeypatch.setattr(tus_repoaccess, 'run', run_spy)

    tus_repoaccess._refresh_ca_trust('/target/userspace')

    assert run_spy.calls == [
        ['chroot', '/target/userspace', '/bin/bash', '-c', 'su - -c update-ca-trust'],
    ]


# ---------------------------------------------------------------------------
# _copy_rhsm_config
# ---------------------------------------------------------------------------
def test_copy_rhsm_config_skipped(monkeypatch):
    run_spy = RunSpy()
    monkeypatch.setattr(tus_repoaccess, 'run', run_spy)
    monkeypatch.setattr(tus_repoaccess.rhsm, 'skip_rhsm', lambda: True)
    context = MockContext()

    tus_repoaccess._copy_rhsm_config(context, '/target/userspace')

    assert not run_spy.calls
    assert not context.copytree_from_calls


def test_copy_rhsm_config_performed(monkeypatch):
    run_spy = RunSpy()
    monkeypatch.setattr(tus_repoaccess, 'run', run_spy)
    monkeypatch.setattr(tus_repoaccess.rhsm, 'skip_rhsm', lambda: False)
    context = MockContext()

    tus_repoaccess._copy_rhsm_config(context, '/target/userspace')

    target_rhsm = os.path.join('/target/userspace', 'etc', 'rhsm')
    assert run_spy.calls == [['rm', '-rf', target_rhsm]]
    assert context.copytree_from_calls == [('/etc/rhsm', target_rhsm)]


# ---------------------------------------------------------------------------
# _merge_repos_preserving_rpm_owned
# ---------------------------------------------------------------------------
def test_merge_repos_preserving_rpm_owned(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    run_spy = RunSpy()
    monkeypatch.setattr(tus_repoaccess, 'run', run_spy)
    monkeypatch.setattr(tus_repoaccess.mounting, 'NspawnActions', MockNspawnActions)
    monkeypatch.setattr(
        tus_repoaccess, '_get_files_owned_by_rpms', lambda ctx, path: ['redhat.repo']
    )
    context = MockContext()

    target_userspace = '/target/userspace'
    tus_repoaccess._merge_repos_preserving_rpm_owned(context, target_userspace)

    target_etc = os.path.join(target_userspace, 'etc')
    target_yum = os.path.join(target_etc, 'yum.repos.d')
    backup_yum = os.path.join(target_etc, 'yum.repos.d.backup')

    assert run_spy.calls == [
        ['mv', target_yum, backup_yum],
        ['mv', os.path.join(backup_yum, 'redhat.repo'), os.path.join(target_yum, 'redhat.repo')],
        ['rm', '-rf', backup_yum],
    ]
    assert context.copytree_from_calls == [('/etc/yum.repos.d', target_yum)]


# ---------------------------------------------------------------------------
# prep_repository_access
# ---------------------------------------------------------------------------
def test_prep_repository_access_orchestration(monkeypatch):
    order = []

    def make_spy(name):
        def _spy(*args):
            order.append((name, args))
        return _spy

    monkeypatch.setattr(tus_repoaccess, '_copy_certificates', make_spy('certs'))
    monkeypatch.setattr(tus_repoaccess, '_refresh_ca_trust', make_spy('ca'))
    monkeypatch.setattr(tus_repoaccess, '_copy_rhsm_config', make_spy('rhsm'))
    monkeypatch.setattr(tus_repoaccess, '_merge_repos_preserving_rpm_owned', make_spy('merge'))

    context = MockContext()
    target_userspace = '/target/userspace'
    tus_repoaccess.prep_repository_access(context, target_userspace)

    assert [name for name, _ in order] == ['certs', 'ca', 'rhsm', 'merge']
    assert order[0][1] == (context, target_userspace)
    assert order[1][1] == (target_userspace,)
    assert order[2][1] == (context, target_userspace)
    assert order[3][1] == (context, target_userspace)


# ---------------------------------------------------------------------------
# _choose_copy_or_link - FROZEN CARVE-OUT characterization tests
# ---------------------------------------------------------------------------
def test_choose_copy_or_link_relative_path_raises():
    with pytest.raises(ValueError):
        tus_repoaccess._choose_copy_or_link('relative/path', '/srcdir')


def test_choose_copy_or_link_broken_symlink_raises(tmp_path):
    link = tmp_path / 'broken'
    os.symlink('/does/not/exist', str(link))

    with pytest.raises(BrokenSymlinkError):
        tus_repoaccess._choose_copy_or_link(str(link), str(tmp_path))


def test_choose_copy_or_link_copy_when_pointee_outside_srcdir(tmp_path):
    srcdir = tmp_path / 'src'
    srcdir.mkdir()
    outside = tmp_path / 'outside.txt'
    outside.write_text('data')

    link = srcdir / 'link'
    os.symlink(str(outside), str(link))

    action, source_path = tus_repoaccess._choose_copy_or_link(str(link), str(srcdir))

    assert action == 'copy'
    assert source_path == os.path.normpath(str(outside))


def test_choose_copy_or_link_link_when_pointee_inside_srcdir(tmp_path):
    srcdir = tmp_path / 'src'
    srcdir.mkdir()
    real = srcdir / 'real.txt'
    real.write_text('data')

    link = srcdir / 'link'
    # A relative symlink whose target lives inside srcdir.
    os.symlink('real.txt', str(link))

    action, corrected_path = tus_repoaccess._choose_copy_or_link(str(link), str(srcdir))

    assert action == 'link'
    assert corrected_path == 'real.txt'


# ---------------------------------------------------------------------------
# FROZEN CARVE-OUT known bug (intentionally out of scope for the redesign).
#
# The multi-hop RPM-owned symlink loop in _copy_certificates never advances its
# pointee (it re-reads src_path instead of pointee on each iteration), so a valid
# multi-hop symlink owned by an rpm is misclassified as broken and skipped rather
# than copied. This xfail documents the correct behaviour (the file SHOULD be
# copied) and is expected to fail against the frozen code.
# ---------------------------------------------------------------------------
@pytest.mark.xfail(reason='Frozen carve-out: multi-hop RPM-owned symlink is misclassified as broken.',
                   strict=True)
def test_copy_certificates_multihop_rpm_symlink_is_copied(tmp_path, monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    run_spy = RunSpy()
    monkeypatch.setattr(tus_repoaccess, 'run', run_spy)
    monkeypatch.setattr(tus_repoaccess.mounting, 'NspawnActions', MockNspawnActions)
    monkeypatch.setattr(tus_repoaccess, '_mkdir_with_copied_mode', lambda path, mode_from: None)
    monkeypatch.setattr(tus_repoaccess, '_copy_decouple', lambda srcdir, dstdir: None)
    monkeypatch.setattr(
        tus_repoaccess, '_get_files_owned_by_rpms', lambda ctx, path, recursive=False: ['a-link']
    )

    target_userspace = str(tmp_path)
    backup_pki = os.path.join(target_userspace, 'etc', 'pki.backup')
    target_pki = os.path.join(target_userspace, 'etc', 'pki')
    os.makedirs(backup_pki)
    os.makedirs(target_pki)

    # Multi-hop chain: backup/a-link -> /etc/pki/b-link -> real file c (all valid).
    os.symlink('/etc/pki/b-link', os.path.join(backup_pki, 'a-link'))
    real_c = os.path.join(target_pki, 'c')
    with open(real_c, 'w') as fobj:
        fobj.write('cert')
    os.symlink('c', os.path.join(target_pki, 'b-link'))

    context = MockContext()
    tus_repoaccess._copy_certificates(context, target_userspace)

    copied = [cmd for cmd in run_spy.calls if cmd[0] == 'cp']
    assert copied, 'expected the multi-hop RPM-owned symlink to be copied'
