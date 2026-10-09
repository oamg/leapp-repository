"""
Unit tests for ``tus_repoaccess`` - cert/repofile access for the built userspace.

The ``/etc/pki`` symlink-decoupling helpers (``_choose_copy_or_link``,
``_copy_symlinks``, ``_copy_decouple``) are a FROZEN CARVE-OUT (CONTRACT.md §11).
``test_copy_decouple`` and the ``_get_files_owned_by_rpms`` tests below are ported
verbatim from the pre-refactor ``unit_test_targetuserspacecreator.py`` so the
frozen behaviour stays pinned byte-for-byte; only the module under test changed
(``tus_userspacegen`` -> ``tus_repoaccess``).
"""

import os
import subprocess
import sys

import pytest

from leapp.libraries.actor import tus_repoaccess
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError

if sys.version_info < (2, 8):
    from pathlib2 import Path
else:
    from pathlib import Path


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


class _MockContext():

    def __init__(self, base_dir, owned_by_rpms):
        self.base_dir = base_dir
        # list of files owned, no base_dir prefixed
        self.owned_by_rpms = owned_by_rpms

    def full_path(self, path):
        return os.path.join(self.base_dir, os.path.abspath(path).lstrip('/'))

    def call(self, cmd):
        assert len(cmd) == 3 and cmd[0] == 'rpm' and cmd[1] == '-qf'
        if cmd[2] in self.owned_by_rpms:
            return {'exit_code': 0}
        raise CalledProcessError(
            "Command failed with exit code 1",
            cmd,
            {'stdout': '', 'stderr': '', 'exit_code': 1},
        )


def test__get_files_owned_by_rpms(monkeypatch):

    def listdir_mocked(path):
        assert path == '/base/dir/some/path'
        return ['fileA', 'fileB.txt', 'test.log', 'script.sh']

    monkeypatch.setattr(os, 'listdir', listdir_mocked)
    logger = logger_mocked()
    monkeypatch.setattr(api, 'current_logger', logger)

    search_dir = '/some/path'
    # output doesn't include full paths
    owned = ['fileA', 'script.sh']
    # but the rpm -qf call happens with the full path
    owned_fullpath = [os.path.join(search_dir, f) for f in owned]
    context = _MockContext('/base/dir', owned_fullpath)

    out = tus_repoaccess._get_files_owned_by_rpms(context, '/some/path', recursive=False)
    assert sorted(owned) == sorted(out)


def test__get_files_owned_by_rpms_recursive(monkeypatch):
    # this is not necessarily accurate, but close enough
    fake_walk = [
        ("/base/dir/etc/pki", ["ca-trust", "tls", "rpm-gpg"], []),
        ("/base/dir/etc/pki/ca-trust", ["extracted", "source"], []),
        ("/base/dir/etc/pki/ca-trust/extracted", ["openssl", "java"], []),
        ("/base/dir/etc/pki/ca-trust/extracted/openssl", [], ["ca-bundle.trust.crt"]),
        ("/base/dir/etc/pki/ca-trust/extracted/java", [], ["cacerts"]),

        ("/base/dir/etc/pki/ca-trust/source", ["anchors", "directory-hash"], []),
        ("/base/dir/etc/pki/ca-trust/source/anchors", [], ["my-ca.crt"]),
        ("/base/dir/etc/pki/ca-trust/extracted/pem/directory-hash", [], [
          "5931b5bc.0", "a94d09e5.0"
        ]),
        ("/base/dir/etc/pki/tls", ["certs", "private"], []),
        ("/base/dir/etc/pki/tls/certs", [], ["server.crt", "ca-bundle.crt"]),
        ("/base/dir/etc/pki/tls/private", [], ["server.key"]),
        ("/base/dir/etc/pki/rpm-gpg", [], [
            "RPM-GPG-KEY-1",
            "RPM-GPG-KEY-2",
        ]),
    ]

    def walk_mocked(path):
        assert path == '/base/dir/etc/pki'
        return fake_walk

    monkeypatch.setattr(os, 'walk', walk_mocked)
    logger = logger_mocked()
    monkeypatch.setattr(api, 'current_logger', logger)

    search_dir = '/etc/pki'
    # output doesn't include full paths
    owned = [
        'tls/certs/ca-bundle.crt',
        'ca-trust/extracted/openssl/ca-bundle.trust.crt',
        'rpm-gpg/RPM-GPG-KEY-1',
        'rpm-gpg/RPM-GPG-KEY-2',
        'ca-trust/extracted/pem/directory-hash/a94d09e5.0',
        'ca-trust/extracted/pem/directory-hash/a94d09e5.0',
    ]
    # the rpm -qf call happens with the full path
    owned_fullpath = [os.path.join(search_dir, f) for f in owned]
    context = _MockContext('/base/dir', owned_fullpath)

    out = tus_repoaccess._get_files_owned_by_rpms(context, search_dir, recursive=True)
    # any directory-hash directory should be skipped
    assert sorted(owned[0:4]) == sorted(out)

    def has_dbgmsg(substr):
        return any(substr in log for log in logger.dbgmsg)

    # test a few
    assert has_dbgmsg(
        "SKIP files in the /base/dir/etc/pki/ca-trust/extracted/pem/directory-hash directory:"
        " Not important for the IPU.",
    )
    assert has_dbgmsg('SKIP the tls/certs/server.crt file: not owned by any rpm')
    assert has_dbgmsg('Found the file owned by an rpm: rpm-gpg/RPM-GPG-KEY-2.')
