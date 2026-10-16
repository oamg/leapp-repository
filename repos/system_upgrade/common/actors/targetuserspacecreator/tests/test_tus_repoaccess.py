import os
import subprocess
from pathlib import Path

import pytest
from test_tus_mock_utils import make_cpe, MockNspawnActions, RunSpy

from leapp.libraries.actor import tus_repoaccess
from leapp.libraries.actor.tus_repoaccess import BrokenSymlinkError
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api


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
                raise make_cpe()
            return {'stdout': self.rpm_owners[queried]}
        return {'stdout': ''}

    def copytree_from(self, src, dst):
        self.copytree_from_calls.append((src, dst))


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


# ---------------------------------------------------------------------------
# Tests for _copy_decouple function
# ---------------------------------------------------------------------------
def traverse_structure(structure, root=Path('/')):
    """
    Given a description of a directory structure, return fullpaths to the
    files and what they link to.

    :param structure: A dict which defined the directory structure.  See below
        for what it looks like.
    :param root: A path to prefix to the files.  On an actual run in production.
        this would be `/` but since we're doing this in a unittest, it needs to
        be a temporary directory.
    :returns: This is a generator, so pairs of (filepath, what it links to) will
        be returned one at a time, each time through the iterable.

    The semantics of `structure` are as follows:

    1. The outermost dictionary encodes the root of a directory structure

    2. Depending on the value for a key in a dict, each key in the dictionary
       denotes the name of either a:
         a) directory -- if value is dict
         b) regular file -- if value is None
         c) symlink -- if a value is str

     3. The value of a symlink entry is a absolute path to a file in the context of
        the structure.

    .. warning:: Empty directories are not returned.
    """
    for filename, links_to in structure.items():
        filepath = root / filename

        if isinstance(links_to, dict):
            yield from traverse_structure(links_to, root=filepath)
        else:
            yield (filepath, links_to)


def assert_directory_structure_matches(root, initial, expected):
    # Assert every file that is supposed to be present is present
    for filepath, links_to in traverse_structure(expected, root=root / 'expected'):
        assert filepath.exists(), "{} was supposed to exist and does not".format(filepath)

        if links_to is None:
            assert filepath.is_file(), "{} was supposed to be a file but is not".format(filepath)
            continue

        assert filepath.is_symlink(), '{} was supposed to be a symlink but is not'.format(filepath)

        # We need to rewrite absolute paths because:
        # * links_to contains an absolute path to the resource where the root
        #   directory is `/`.
        # * In our test case, the source resource is rooted in a temporary
        #   directory rather than '/'.
        # * The temporary directory name is root / 'initial'.
        # So we rewrite the initial `/` to be `root/{initial}` to account for
        # that.  In production, the root directory will be `/` so no rewriting
        # will happen there.
        #
        if links_to.startswith('/'):
            links_to = str(root / 'initial' / links_to.lstrip('/'))

        actual_links_to = os.readlink(str(filepath))
        assert actual_links_to == str(links_to), (
            '{} linked to {} instead of {}'.format(filepath, actual_links_to, links_to))

    # Assert there are no extra files
    result_dir = str(root / 'expected')
    for fileroot, dummy_dirs, files in os.walk(result_dir):
        for filename in files:
            dir_path = os.path.relpath(fileroot, result_dir).split('/')

            cwd = expected
            for directory in dir_path:
                cwd = cwd[directory]

            assert filename in cwd

            filepath = os.path.join(fileroot, filename)
            if os.path.islink(filepath):
                links_to = os.readlink(filepath)
                # We rewrite absolute paths because the root directory is in
                # a temp dir instead of `/` in the unittest.  See the comment
                # where we rewrite `links_to` for the previous loop in this
                # function for complete details.
                if links_to.startswith('/'):
                    links_to = '/' + os.path.relpath(links_to, str(root / 'initial'))
                assert cwd[filename] == links_to


@pytest.fixture
def temp_directory_layout(tmp_path, initial_structure):
    for filepath, links_to in traverse_structure(initial_structure, root=tmp_path / 'initial'):
        # Directories are inlined by traverse_structure so we need to create
        # them here
        file_path = tmp_path / filepath
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Real file
        if links_to is None:
            file_path.touch()
            continue

        # Symlinks
        if links_to.startswith('/'):
            # Absolute symlink
            file_path.symlink_to(tmp_path / 'initial' / links_to.lstrip('/'))
        else:
            # Relative symlink
            file_path.symlink_to(links_to)

    (tmp_path / 'expected').mkdir()
    assert (tmp_path / 'expected').exists()

    return tmp_path


# The semantics of initial_structure and expected_structure are defined in the
@pytest.mark.parametrize('initial_structure,expected_structure', [
    (pytest.param(
        {
            'dir': {
                'fileA': None
            }
        },
        {
            'dir': {
                'fileA': None
            },
        },
        id="Copy_a_regular_file"
    )),
    # Absolute symlink tests
    (pytest.param(
        {
            'dir': {
                'fileA': '/nonexistent'
            }
        },
        {
            'dir': {},
        },
        id="Absolute_do_not_copy_a_broken_symlink"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': '/dir/fileB',
                'fileB': '/nonexistent'
            }
        },
        {
            'dir': {}
        },
        id="Absolute_do_not_copy_a_chain_of_broken_symlinks"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': '/nonexistent-dir/nonexistent'
            },
        },
        {
            'dir': {},
        },
        id="Absolute_do_not_copy_a_broken_symlink_to_a_nonexistent_directory"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': '/dir/fileB',
                'fileB': '/dir/fileC',
                'fileC': '/dir/fileA',
                'fileD': '/dir/fileD',
            }
        },
        {
            'dir': {}
        },
        id="Absolute_do_not_copy_circular_symlinks"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': '/dir/fileB',
                'fileB': None
            }
        },
        {
            'dir': {
                'fileA': '/dir/fileB',
                'fileB': None
            }
        },
        id="Absolute_copy_a_regular_symlink"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': '/dir/fileB',
                'fileB': '/dir/fileC',
                'fileC': None
            }
        },
        {
            'dir': {
                'fileA': '/dir/fileB',
                'fileB': '/dir/fileC',
                'fileC': None
            }
        },
        id="Absolute_copy_a_chain_of_symlinks"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': '/dir/fileB',
                'fileB': '/dir/fileC',
                'fileC': '/outside/fileOut',
                'fileE': None
            },
            'outside': {
                'fileOut': '/outside/fileD',
                'fileD': '/dir/fileE'
            }
        },
        {
            'dir': {
                'fileA': '/dir/fileB',
                'fileB': '/dir/fileC',
                'fileC': '/dir/fileE',
                'fileE': None,
            }
        },
        id="Absolute_copy_a_link_to_a_file_outside_the_considered_directory_as_file"
    )),
    (pytest.param(
        {
            'dir': {
                'nested': {
                    'fileA': '/dir/nested/fileB',
                    'fileB': '/dir/nested/fileC',
                    'fileC': '/outside/fileOut',
                    'fileE': None
                }
            },
            'outside': {
                'fileOut': '/outside/fileD',
                'fileD': '/dir/nested/fileE'
            }
        },
        {
            'dir': {
                'nested': {
                    'fileA': '/dir/nested/fileB',
                    'fileB': '/dir/nested/fileC',
                    'fileC': '/dir/nested/fileE',
                    'fileE': None
                }
            }
        },
        id="Absolute_copy_a_link_to_a_file_outside_with_a_nested_structure_within_the_source_dir"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': '/dir/fileB',
                'fileB': '/dir/fileC',
                'fileC': '/outside/nested/fileOut',
                'fileE': None
            },
            'outside': {
                'nested': {
                    'fileOut': '/outside/nested/fileD',
                    'fileD': '/dir/fileE'
                }
            }
        },
        {
            'dir': {
                'fileA': '/dir/fileB',
                'fileB': '/dir/fileC',
                'fileC': '/dir/fileE',
                'fileE': None,
            }
        },
        id="Absolute_copy_a_link_to_a_file_outside_with_a_nested_structure_in_the_outside_dir"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': '/outside/fileOut',
                'fileB': None,
            },
            'outside': {
                'fileOut': '../dir/fileB',
            },
        },
        {
            'dir': {
                'fileA': '/dir/fileB',
                'fileB': None,
            },
        },
        id="Absolute_symlink_that_leaves_the_directory_but_returns_with_relative_outside"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': '/outside/fileB',
                'fileB': None,
            },
            'outside': '/dir',
        },
        {
            'dir': {
                'fileA': '/dir/fileB',
                'fileB': None,
            },
        },
        id="Absolute_symlink_to_a_file_inside_via_a_symlink_to_the_rootdir"
    )),
    # This should be fixed but not necessarily for this release.
    # It makes sure that when we have two separate links to the
    # same file outside of /etc/pki, one of the links is copied
    # as a real file and the other is made a link to the copy.
    # (Right now, the real file is copied in place of both links.)
    # (pytest.param(
    #     {
    #         'dir': {
    #             'fileA': '/outside/fileC',
    #             'fileB': '/outside/fileC',
    #         },
    #         'outside': {
    #             'fileC': None,
    #         },
    #     },
    #     {
    #         'dir': {
    #             'fileA': None,
    #             'fileB': '/dir/fileA',
    #         },
    #     },
    #     id="Absolute_two_symlinks_to_the_same_copied_file"
    # )),
    (pytest.param(
        {
            'dir': {
                'fileA': None,
                'link_to_dir': '/dir/inside',
                'inside': {
                    'fileB': None,
                },
            },
        },
        {
            'dir': {
                'fileA': None,
                'link_to_dir': '/dir/inside',
                'inside': {
                    'fileB': None,
                },
            },
        },
        id="Absolute_symlink_to_a_dir_inside"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': None,
                'link_to_dir': '/outside',
            },
            'outside': {
                'fileB': None,
            },
        },
        {
            'dir': {
                'fileA': None,
                'link_to_dir': {
                    'fileB': None,
                },
            },
        },
        id="Absolute_symlink_to_a_dir_outside"
    )),
    (pytest.param(
        # This one is very tricky:
        # * The user has made /etc/pki a symlink to some other directory that
        #   they keep certificates.
        # * In the target system, we are going to make /etc/pki an actual
        #   directory with the contents that the actual directory on the host
        #   system had.
        {
            'dir': '/funkydir',
            'funkydir': {
                'fileA': '/funkydir/fileB',
                'fileB': None,
            },
        },
        {
            'dir': {
                'fileA': '/dir/fileB',
                'fileB': None,
            },
        },
        id="Absolute_symlink_where_srcdir_is_a_symlink_on_the_host_system"
    )),
    # Relative symlink tests
    (pytest.param(
        {
            'dir': {
                'fileA': 'nonexistent'
            },
        },
        {
            'dir': {},
        },
        id="Relative_do_not_copy_a_broken_symlink"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': 'fileB',
                'fileB': 'nonexistent'
            }
        },
        {
            'dir': {}
        },
        id="Relative_do_not_copy_a_chain_of_broken_symlinks"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': 'nonexistent-dir/nonexistent'
            },
        },
        {
            'dir': {},
        },
        id="Relative_do_not_copy_a_broken_symlink_to_a_nonexistent_directory"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': 'fileB',
                'fileB': 'fileC',
                'fileC': 'fileA',
                'fileD': 'fileD',
            }
        },
        {
            'dir': {}
        },
        id="Relative_do_not_copy_circular_symlinks"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': 'fileB',
                'fileB': None,
            },
        },
        {
            'dir': {
                'fileA': 'fileB',
                'fileB': None,
            },
        },
        id="Relative_copy_a_regular_symlink_to_a_file_in_the_same_directory"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': 'dir2/../fileB',
                'fileB': None,
                'dir2': {
                    'fileC': None
                },
            },
        },
        {
            'dir': {
                'fileA': 'fileB',
                'fileB': None,
                'dir2': {
                    'fileC': None
                },
            },
        },
        id="Relative_symlink_with_parent_dir_but_still_in_same_directory"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': 'fileB',
                'fileB': 'fileC',
                'fileC': None
            }
        },
        {
            'dir': {
                'fileA': 'fileB',
                'fileB': 'fileC',
                'fileC': None
            }
        },
        id="Relative_copy_a_chain_of_symlinks"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': 'fileB',
                'fileB': 'fileC',
                'fileC': '../outside/fileOut',
                'fileE': None
            },
            'outside': {
                'fileOut': 'fileD',
                'fileD': '../dir/fileE'
            }
        },
        {
            'dir': {
                'fileA': 'fileB',
                'fileB': 'fileC',
                'fileC': 'fileE',
                'fileE': None,
            }
        },
        id="Relative_copy_a_link_to_a_file_outside_the_considered_directory_as_file"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': '../outside/fileOut',
                'fileB': None,
            },
            'outside': {
                'fileOut': None,
            },
        },
        {
            'dir': {
                'fileA': None,
                'fileB': None,
            },
        },
        id="Relative_symlink_to_outside"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': 'nested/fileB',
                'nested': {
                    'fileB': None,
                },
            },
        },
        {
            'dir': {
                'fileA': 'nested/fileB',
                'nested': {
                    'fileB': None,
                },
            },
        },
        id="Relative_copy_a_symlink_to_a_file_in_a_subdir"
    )),
    (pytest.param(
        {
            'dir': {
                'fileF': 'nested/fileC',
                'nested': {
                    'fileA': 'fileB',
                    'fileB': 'fileC',
                    'fileC': '../../outside/fileOut',
                    'fileE': None,
                }
            },
            'outside': {
                'fileOut': 'fileD',
                'fileD': '../dir/nested/fileE',
            }
        },
        {
            'dir': {
                'fileF': 'nested/fileC',
                'nested': {
                    'fileA': 'fileB',
                    'fileB': 'fileC',
                    'fileC': 'fileE',
                    'fileE': None,
                }
            }
        },
        id="Relative_copy_a_link_to_a_file_outside_with_a_nested_structure_within_the_source_dir"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': 'fileB',
                'fileB': 'fileC',
                'fileC': '../outside/nested/fileOut',
                'fileE': None
            },
            'outside': {
                'nested': {
                    'fileOut': 'fileD',
                    'fileD': '../../dir/fileE'
                }
            }
        },
        {
            'dir': {
                'fileA': 'fileB',
                'fileB': 'fileC',
                'fileC': 'fileE',
                'fileE': None,
            }
        },
        id="Relative_copy_a_link_to_a_file_outside_with_a_nested_structure_in_the_outside_dir"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': '../outside/fileOut',
                'fileB': None,
            },
            'outside': {
                'fileOut': '../dir/fileB',
            },
        },
        {
            'dir': {
                'fileA': 'fileB',
                'fileB': None,
            },
        },
        id="Relative_symlink_that_leaves_the_directory_but_returns"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': '../outside/fileOut',
                'fileB': None,
            },
            'outside': {
                'fileOut': '/dir/fileB',
            },
        },
        {
            'dir': {
                'fileA': 'fileB',
                'fileB': None,
            },
        },
        id="Relative_symlink_that_leaves_the_directory_but_returns_with_absolute_outside"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': '../outside/fileB',
                'fileB': None,
            },
            'outside': '/dir',
        },
        {
            'dir': {
                'fileA': 'fileB',
                'fileB': None,
            },
        },
        id="Relative_symlink_to_a_file_inside_via_a_symlink_to_the_rootdir"
    )),
    # This should be fixed but not necessarily for this release.
    # It makes sure that when we have two separate links to the
    # same file outside of /etc/pki, one of the links is copied
    # as a real file and the other is made a link to the copy.
    # (Right now, the real file is copied in place of both links.)
    # (pytest.param(
    #     {
    #         'dir': {
    #             'fileA': '../outside/fileC',
    #             'fileB': '../outside/fileC',
    #         },
    #         'outside': {
    #             'fileC': None,
    #         },
    #     },
    #     {
    #         'dir': {
    #             'fileA': None,
    #             'fileB': 'fileA',
    #         },
    #     },
    #     id="Relative_two_symlinks_to_the_same_copied_file"
    # )),
    (pytest.param(
        {
            'dir': {
                'fileA': None,
                'link_to_dir': '../outside',
            },
            'outside': {
                'fileB': None,
            },
        },
        {
            'dir': {
                'fileA': None,
                'link_to_dir': {
                    'fileB': None,
                },
            },
        },
        id="Relative_symlink_to_a_dir_outside"
    )),
    (pytest.param(
        {
            'dir': {
                'fileA': None,
                'link_to_dir': 'inside',
                'inside': {
                    'fileB': None,
                },
            },
        },
        {
            'dir': {
                'fileA': None,
                'link_to_dir': 'inside',
                'inside': {
                    'fileB': None,
                },
            },
        },
        id="Relative_symlink_to_a_dir_inside"
    )),
    (pytest.param(
        # This one is very tricky:
        # * The user has made /etc/pki a symlink to some other directory that
        #   they keep certificates.
        # * In the target system, we are going to make /etc/pki an actual
        #   directory with the contents that the actual directory on the host
        #   system had.
        {
            'dir': 'funkydir',
            'funkydir': {
                'fileA': 'fileB',
                'fileB': None,
            },
        },
        {
            'dir': {
                'fileA': 'fileB',
                'fileB': None,
            },
        },
        id="Relative_symlink_where_srcdir_is_a_symlink_on_the_host_system"
    )),
]
)
def test_copy_decouple(monkeypatch, temp_directory_layout, initial_structure, expected_structure):

    def run_mocked(command):
        subprocess.check_call(
            ' '.join(command),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    monkeypatch.setattr(tus_repoaccess, 'run', run_mocked)
    expected_dir = temp_directory_layout / 'expected' / 'dir'
    expected_dir.mkdir()
    tus_repoaccess._copy_decouple(
            str(temp_directory_layout / 'initial' / 'dir'),
            str(expected_dir),
            )

    try:
        assert_directory_structure_matches(temp_directory_layout, initial_structure, expected_structure)
    except AssertionError:
        # For debugging purposes, print out the entire directory structure if an
        # assertion failed.
        for rootdir, dirs, files in os.walk(temp_directory_layout):
            for d in dirs:
                print(os.path.join(rootdir, d))
            for f in files:
                filename = os.path.join(rootdir, f)
                print("  {}".format(filename))
                if os.path.islink(filename):
                    print("    => Links to: {}".format(os.readlink(filename)))

        # Then re-raise the assertion
        raise
