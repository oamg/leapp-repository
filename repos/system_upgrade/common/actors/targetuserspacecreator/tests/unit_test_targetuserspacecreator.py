from __future__ import division, print_function

import os
import subprocess
import sys
import tempfile
from collections import namedtuple

import pytest

from leapp import models, reporting
from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.actor import userspacegen
from leapp.libraries.common import distro, overlaygen, repofileutils, rhsm
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked, produce_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.utils.deprecation import suppress_deprecation

if sys.version_info < (2, 8):
    from pathlib2 import Path
else:
    from pathlib import Path


CUR_DIR = os.path.dirname(os.path.abspath(__file__))
_CERTS_PATH = os.path.join(CUR_DIR, '../../../files', userspacegen.PROD_CERTS_FOLDER)
_DEFAULT_CERT_PATH = os.path.join(_CERTS_PATH, '8.1', '479.pem')


@pytest.fixture
def adjust_cwd():
    previous_cwd = os.getcwd()
    os.chdir(os.path.join(CUR_DIR, "../"))
    yield
    os.chdir(previous_cwd)


class MockedMountingBase(object):
    def __init__(self, **dummy_kwargs):
        self.called_copytree_from = []
        self.target = ''

    def open(self, fullpath, *args, **kwargs):
        return open(self, fullpath, *args, **kwargs)

    def copytree_from(self, src, dst):
        self.called_copytree_from.append((src, dst))

    def __call__(self, **dummy_kwarg):
        yield self

    def call(self, *args, **kwargs):
        return {'stdout': ''}

    def nspawn(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        pass


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
# traverse_structure() docstring.
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

    monkeypatch.setattr(userspacegen, 'run', run_mocked)
    expected_dir = temp_directory_layout / 'expected' / 'dir'
    expected_dir.mkdir()
    userspacegen._copy_decouple(
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


@pytest.mark.parametrize('result,dst_ver,arch,prod_type', [
    (os.path.join(_CERTS_PATH, '8.1', '479.pem'), '8.1', architecture.ARCH_X86_64, 'ga'),
    (os.path.join(_CERTS_PATH, '8.1', '419.pem'), '8.1', architecture.ARCH_ARM64, 'ga'),
    (os.path.join(_CERTS_PATH, '8.1', '279.pem'), '8.1', architecture.ARCH_PPC64LE, 'ga'),
    (os.path.join(_CERTS_PATH, '8.2', '479.pem'), '8.2', architecture.ARCH_X86_64, 'ga'),
    (os.path.join(_CERTS_PATH, '8.5', '486.pem'), '8.5', architecture.ARCH_X86_64, 'beta'),
    (os.path.join(_CERTS_PATH, '8.2', '72.pem'), '8.2', architecture.ARCH_S390X, 'ga'),
    (os.path.join(_CERTS_PATH, '8.5', '433.pem'), '8.5', architecture.ARCH_S390X, 'beta'),
])
def test_get_product_certificate_path(monkeypatch, adjust_cwd, result, dst_ver, arch, prod_type):
    envars = {'LEAPP_DEVEL_TARGET_PRODUCT_TYPE': prod_type}
    curr_actor_mocked = CurrentActorMocked(dst_ver=dst_ver, arch=arch, envars=envars)
    monkeypatch.setattr(userspacegen.api, 'current_actor', curr_actor_mocked)
    assert userspacegen._get_product_certificate_path() in result


def test_get_product_certificate_path_nonrhel(monkeypatch):
    actor = CurrentActorMocked(release_id='notrhel')
    monkeypatch.setattr(userspacegen.api, 'current_actor', actor)
    path = userspacegen._get_product_certificate_path()
    assert path is None


@suppress_deprecation(models.RequiredTargetUserspacePackages)
def _gen_packages_msgs():
    _cfiles = [
        models.CopyFile(src='/path/src', dst='/path/dst'),
        models.CopyFile(src='/path/foo', dst='/path/bar'),
    ]
    return [
        models.RequiredTargetUserspacePackages(),
        models.RequiredTargetUserspacePackages(packages=['pkgA']),
        models.RequiredTargetUserspacePackages(packages=['pkgB', 'pkgsC']),
        models.RequiredTargetUserspacePackages(packages=['pkgD']),
        models.TargetUserSpacePreupgradeTasks(),
        models.TargetUserSpacePreupgradeTasks(install_rpms=['pkgA']),
        models.TargetUserSpacePreupgradeTasks(install_rpms=['pkgB', 'pkgsC']),
        models.TargetUserSpacePreupgradeTasks(install_rpms=['pkgD', 'pkgE'], copy_files=[_cfiles[0]]),
        models.TargetUserSpacePreupgradeTasks(copy_files=_cfiles),
    ]


_PACKAGES_MSGS = _gen_packages_msgs()
_RHSMINFO_MSG = models.RHSMInfo(attached_skus=['testing-sku'])
_RHUIINFO_MSG = models.RHUIInfo(provider='aws',
                                src_client_pkg_names=['rh-amazon-rhui-client'],
                                target_client_pkg_names=['rh-amazon-rhui-client'],
                                target_client_setup_info=models.TargetRHUISetupInfo(
                                    preinstall_tasks=models.TargetRHUIPreInstallTasks(),
                                    postinstall_tasks=models.TargetRHUIPostInstallTasks()))
_XFS_MSG = models.XFSPresence()
_STORAGEINFO_MSG = models.StorageInfo()
_CTRF_MSGS = [
    models.CustomTargetRepositoryFile(file='rfileA'),
    models.CustomTargetRepositoryFile(file='rfileB'),
]
_SAEE = StopActorExecutionError
_SAE = StopActorExecution


class MockedConsume(object):
    def __init__(self, *args):
        self._msgs = []
        for arg in args:
            if not arg:
                continue
            if isinstance(arg, list):
                self._msgs.extend(arg)
            else:
                self._msgs.append(arg)

    def __call__(self, model):
        return iter([msg for msg in self._msgs if isinstance(msg, model)])


testInData = namedtuple(
    'TestInData', ['pkg_msgs', 'rhsm_info', 'rhui_info', 'xfs', 'storage', 'custom_repofiles']
)


# NOTE: tests cover know new, deprecated, and both ways how to require packages
# that should be installed to create the target userspace. Cases which could be
# removed completely after the drop of the deprecated functionality, are marked
# with the `# dep` str.
@pytest.mark.parametrize('raised,no_rhsm,testdata', [
    # valid cases with RHSM
    (None, '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    (None, '0', testInData(_PACKAGES_MSGS[:4], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),   # dep
    (None, '0', testInData(_PACKAGES_MSGS[4:8], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),  # dep
    (None, '0', testInData(_PACKAGES_MSGS[0], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    (None, '0', testInData(_PACKAGES_MSGS[4], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),    # dep
    (None, '0', testInData([], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    (None, '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, None, _STORAGEINFO_MSG, None)),
    (None, '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, _CTRF_MSGS)),
    (None, '0', testInData(_PACKAGES_MSGS[0], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, _CTRF_MSGS)),
    (None, '0', testInData(_PACKAGES_MSGS[4], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, _CTRF_MSGS)),  # dep
    (None, '0', testInData([], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, _CTRF_MSGS)),
    (None, '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, None, _STORAGEINFO_MSG, _CTRF_MSGS)),

    # valid cases without RHSM (== skip_rhsm)
    (None, '1', testInData(_PACKAGES_MSGS, None, _RHUIINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG, None)),
    (None, '1', testInData(_PACKAGES_MSGS[:4], None, _RHUIINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG, None)),   # dep
    (None, '1', testInData(_PACKAGES_MSGS[4:8], None, _RHUIINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG, None)),  # dep
    (None, '1', testInData(_PACKAGES_MSGS, None, _RHUIINFO_MSG, None, _STORAGEINFO_MSG, None)),
    (None, '1', testInData([], None, _RHUIINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG, None)),
    (None, '1', testInData([], None, _RHUIINFO_MSG, None, _STORAGEINFO_MSG, None)),
    (None, '1', testInData(_PACKAGES_MSGS, None, _RHUIINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG, _CTRF_MSGS)),
    (None, '1', testInData(_PACKAGES_MSGS, None, _RHUIINFO_MSG, None, _STORAGEINFO_MSG, _CTRF_MSGS)),
    (None, '1', testInData([], None, _RHUIINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG, _CTRF_MSGS)),
    (None, '1', testInData([], None, _RHUIINFO_MSG, None, _STORAGEINFO_MSG, _CTRF_MSGS)),

    # no-rhsm but RHSMInfo defined (should be _RHSMINFO_MSG)
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS[0], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG,
                                             None)),
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS[4], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG,
                                             None)),  # dep
    ((_SAEE, 'RHSM is not'), '1', testInData([], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, None, _STORAGEINFO_MSG, None)),
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG,
                                             _CTRF_MSGS)),
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS[0], _RHSMINFO_MSG, None, _XFS_MSG,
                                             _STORAGEINFO_MSG, _CTRF_MSGS)),
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS[4], _RHSMINFO_MSG, None, _XFS_MSG,
                                             _STORAGEINFO_MSG, _CTRF_MSGS)),  # dep
    ((_SAEE, 'RHSM is not'), '1', testInData([], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, _CTRF_MSGS)),
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, None, _STORAGEINFO_MSG, _CTRF_MSGS)),

    # missing RHSMInfo but it should exist
    # NOTE: should be this Error?!
    ((_SAE, 'RHSM information'), '0', testInData(_PACKAGES_MSGS, None, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    ((_SAE, 'RHSM information'), '0', testInData(_PACKAGES_MSGS, None, None, None, _STORAGEINFO_MSG, None)),
    ((_SAE, 'RHSM information'), '0', testInData([], None, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    ((_SAE, 'RHSM information'), '0', testInData([], None, None, None, _STORAGEINFO_MSG, None)),

    # in the end, error when StorageInfo is missing
    ((_SAEE, 'No storage'), '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, _XFS_MSG, None, None)),
    ((_SAEE, 'No storage'), '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, None, None, None)),
    ((_SAEE, 'No storage'), '0', testInData([], _RHSMINFO_MSG, None, _XFS_MSG, None, None)),
    ((_SAEE, 'No storage'), '0', testInData([], _RHSMINFO_MSG, None, None, None, None)),
    ((_SAEE, 'No storage'), '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, _XFS_MSG, None, _CTRF_MSGS)),
    ((_SAEE, 'No storage'), '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, None, None, _CTRF_MSGS)),
    ((_SAEE, 'No storage'), '0', testInData([], _RHSMINFO_MSG, None, _XFS_MSG, None, _CTRF_MSGS)),
    ((_SAEE, 'No storage'), '0', testInData([], _RHSMINFO_MSG, None, None, None, _CTRF_MSGS)),
])
def test_consume_data(monkeypatch, raised, no_rhsm, testdata):
    # do not write never into testdata inside the test !!
    xfs = testdata.xfs
    custom_repofiles = testdata.custom_repofiles
    _exp_pkgs = {'dnf', 'dnf-command(config-manager)', 'util-linux'}
    _exp_files = []

    def _get_pkgs(msg):
        if isinstance(msg, models.TargetUserSpacePreupgradeTasks):
            return msg.install_rpms
        return msg.packages

    def _get_files(msg):
        if isinstance(msg, models.TargetUserSpacePreupgradeTasks):
            return msg.copy_files
        return []

    def _cfiles2set(cfiles):
        return {(i.src, i.dst) for i in cfiles}

    if isinstance(testdata.pkg_msgs, list):
        for msg in testdata.pkg_msgs:
            _exp_pkgs.update(_get_pkgs(msg))
            _exp_files += _get_files(msg)
    else:
        _exp_pkgs.update(_get_pkgs(testdata.pkg_msgs))
        _exp_files += _get_files(testdata.pkg_msgs)
    mocked_consume = MockedConsume(testdata.pkg_msgs,
                                   testdata.rhsm_info,
                                   testdata.rhui_info,
                                   xfs,
                                   testdata.storage,
                                   custom_repofiles)

    monkeypatch.setattr(userspacegen.api, 'consume', mocked_consume)
    monkeypatch.setattr(userspacegen.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked(envars={'LEAPP_NO_RHSM': no_rhsm}))
    if not xfs:
        xfs = models.XFSPresence()
    if not custom_repofiles:
        custom_repofiles = []
    if not raised:
        result = userspacegen._InputData()
        assert result.packages == _exp_pkgs
        assert _cfiles2set(result.files) == _cfiles2set(_exp_files)
        assert result.rhsm_info == testdata.rhsm_info
        assert result.rhui_info == testdata.rhui_info
        assert result.xfs_info == xfs
        assert result.storage_info == testdata.storage
        assert result.custom_repofiles == custom_repofiles
        assert not userspacegen.api.current_logger.warnmsg
        assert not userspacegen.api.current_logger.errmsg
    else:
        with pytest.raises(raised[0]) as err:
            userspacegen._InputData()
        if isinstance(err.value, StopActorExecutionError):
            assert raised[1] in err.value.message
        else:
            assert userspacegen.api.current_logger.warnmsg
            assert any([raised[1] in x for x in userspacegen.api.current_logger.warnmsg])


@pytest.mark.skip(reason="Currently not implemented in the actor. It's TODO.")
@suppress_deprecation(models.RHELTargetRepository)
def test_gather_target_repositories(monkeypatch):
    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked())
    # The available RHSM repos
    monkeypatch.setattr(rhsm, 'get_available_repo_ids', lambda x: ['repoidX', 'repoidY', 'repoidZ'])
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: False)
    # The required RHEL repos based on the repo mapping and PES data + custom repos required by third party actors
    monkeypatch.setattr(userspacegen.api, 'consume', lambda x: iter([models.TargetRepositories(
        rhel_repos=[models.RHELTargetRepository(repoid='repoidX'),
                    models.RHELTargetRepository(repoid='repoidY')],
        custom_repos=[models.CustomTargetRepository(repoid='repoidCustom')])]))

    target_repoids = userspacegen.gather_target_repositories(None, None)

    assert target_repoids == ['repoidX', 'repoidY', 'repoidCustom']


def test_gather_target_repositories_none_available(monkeypatch):

    mocked_produce = produce_mocked()
    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(userspacegen.api.current_actor(), 'produce', mocked_produce)
    monkeypatch.setattr(rhsm, 'get_available_repo_ids', lambda x: [])
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: False)
    with pytest.raises(StopActorExecution):
        userspacegen.gather_target_repositories(None, None)
        assert mocked_produce.called
        reports = [m.report for m in mocked_produce.model_instances if isinstance(m, reporting.Report)]
        inhibitors = [m for m in reports if 'INHIBITOR' in m.get('flags', ())]
        assert len(inhibitors) == 1
        assert inhibitors[0].get('title', '') == 'Cannot find required basic RHEL target repositories.'


@suppress_deprecation(models.RHELTargetRepository)
def test_gather_target_repositories_rhui(monkeypatch):

    indata = testInData(
        _PACKAGES_MSGS, _RHSMINFO_MSG, _RHUIINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG, None
    )

    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(userspacegen, '_get_all_available_repoids', lambda x: [])
    monkeypatch.setattr(
        userspacegen,
        "_get_distro_available_repoids",
        lambda dummy_context, dummy_indata: {"rhui-1", "rhui-2", "rhui-3"},
    )
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: True)
    monkeypatch.setattr(
        userspacegen.api, 'consume', lambda x: iter(
            [models.TargetRepositories(
                rhel_repos=[
                    models.RHELTargetRepository(repoid='rhui-1'),
                    models.RHELTargetRepository(repoid='rhui-2')
                ],
                distro_repos=[
                    models.DistroTargetRepository(repoid='rhui-1'),
                    models.DistroTargetRepository(repoid='rhui-2')
                ]
            )
            ])
    )
    target_repoids = userspacegen.gather_target_repositories(None, indata)
    assert target_repoids == set(['rhui-1', 'rhui-2'])


@suppress_deprecation(models.RHELTargetRepository)
def test_gather_target_repositories_baseos_appstream_not_available(monkeypatch):
    # If the repos that Leapp identifies as required for the upgrade (based on the repo mapping and PES data) are not
    # available, an exception shall be raised

    indata = testInData(
        _PACKAGES_MSGS, _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None
    )
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: False)

    mocked_produce = produce_mocked()
    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(userspacegen.api.current_actor(), 'produce', mocked_produce)
    # The available RHSM repos
    monkeypatch.setattr(rhsm, 'get_available_repo_ids', lambda x: ['repoidA', 'repoidB', 'repoidC'])
    # The required RHEL repos based on the repo mapping and PES data + custom repos required by third party actors
    monkeypatch.setattr(userspacegen.api, 'consume', lambda x: iter([models.TargetRepositories(
        rhel_repos=[models.RHELTargetRepository(repoid='repoidX'),
                    models.RHELTargetRepository(repoid='repoidY')],
        custom_repos=[models.CustomTargetRepository(repoid='repoidCustom')])]))

    with pytest.raises(StopActorExecution):
        userspacegen.gather_target_repositories(None, indata)
    assert mocked_produce.called
    reports = [m.report for m in mocked_produce.model_instances if isinstance(m, reporting.Report)]
    inhibitors = [m for m in reports if 'inhibitor' in m.get('groups', ())]
    assert len(inhibitors) == 1
    assert inhibitors[0].get('title', '') == 'Cannot find required basic RHEL target repositories.'
    # Now test the case when either of AppStream and BaseOs is not available, upgrade should be inhibited
    mocked_produce = produce_mocked()
    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(userspacegen.api.current_actor(), 'produce', mocked_produce)
    monkeypatch.setattr(rhsm, 'get_available_repo_ids', lambda x: ['repoidA', 'repoidB', 'repoidC-appstream'])
    monkeypatch.setattr(userspacegen.api, 'consume', lambda x: iter([models.TargetRepositories(
        rhel_repos=[models.RHELTargetRepository(repoid='repoidC-appstream'),
                    models.RHELTargetRepository(repoid='repoidA')],
        custom_repos=[models.CustomTargetRepository(repoid='repoidCustom')])]))
    with pytest.raises(StopActorExecution):
        userspacegen.gather_target_repositories(None, indata)
    reports = [m.report for m in mocked_produce.model_instances if isinstance(m, reporting.Report)]
    inhibitors = [m for m in reports if 'inhibitor' in m.get('groups', ())]
    assert len(inhibitors) == 1
    assert inhibitors[0].get('title', '') == 'Cannot find required basic RHEL target repositories.'
    mocked_produce = produce_mocked()
    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(userspacegen.api.current_actor(), 'produce', mocked_produce)
    monkeypatch.setattr(rhsm, 'get_available_repo_ids', lambda x: ['repoidA', 'repoidB', 'repoidC-baseos'])
    monkeypatch.setattr(userspacegen.api, 'consume', lambda x: iter([models.TargetRepositories(
        rhel_repos=[models.RHELTargetRepository(repoid='repoidC-baseos'),
                    models.RHELTargetRepository(repoid='repoidA')],
        custom_repos=[models.CustomTargetRepository(repoid='repoidCustom')])]))
    with pytest.raises(StopActorExecution):
        userspacegen.gather_target_repositories(None, indata)
    reports = [m.report for m in mocked_produce.model_instances if isinstance(m, reporting.Report)]
    inhibitors = [m for m in reports if 'inhibitor' in m.get('groups', ())]
    assert len(inhibitors) == 1
    assert inhibitors[0].get('title', '') == 'Cannot find required basic RHEL target repositories.'


def test__get_distro_available_repoids_norhsm_norhui(monkeypatch):
    """
    Empty set should be returned when on rhel and skip_rhsm == True.
    """
    monkeypatch.setattr(
        userspacegen.api, "current_actor", CurrentActorMocked(release_id="rhel")
    )
    monkeypatch.setattr(userspacegen.api.current_actor(), 'produce', produce_mocked())

    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: True)
    monkeypatch.setattr(distro, 'get_target_distro_repoids', lambda ctx: [])

    indata = testInData(_PACKAGES_MSGS, None, None, _XFS_MSG, _STORAGEINFO_MSG, None)
    # NOTE: context is not used without rhsm, for simplicity setting to None
    repoids = userspacegen._get_distro_available_repoids(None, indata)
    assert repoids == set()


@pytest.mark.parametrize(
    "distro_id,skip_rhsm", [("rhel", False), ("centos", True), ("almalinux", True)]
)
def test__get_distro_available_repoids_nobaserepos_inhibit(
    monkeypatch, distro_id, skip_rhsm
):
    """
    Test that get_distro_available repoids reports and raises if there are no base repos.
    """
    monkeypatch.setattr(
        userspacegen.api, "current_actor", CurrentActorMocked(release_id=distro_id)
    )
    monkeypatch.setattr(userspacegen.api.current_actor(), 'produce', produce_mocked())
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: skip_rhsm)
    monkeypatch.setattr(distro, 'get_target_distro_repoids', lambda ctx: [])

    indata = testInData(_PACKAGES_MSGS, None, None, _XFS_MSG, _STORAGEINFO_MSG, None)
    with pytest.raises(StopActorExecution):
        # NOTE: context is not used without rhsm, for simplicity setting to None
        userspacegen._get_distro_available_repoids(None, indata)

        # TODO adjust the asserts when the report is made distro agnostic
        assert reporting.create_report.called == 1
        report = reporting.create_report.reports[0]
        assert "Cannot find required basic RHEL target repositories" in report["title"]
        assert reporting.Groups.INHIBITOR in report["groups"]


def mocked_consume_data():
    packages = {'dnf', 'dnf-command(config-manager)', 'pkgA', 'pkgB'}
    rhsm_info = _RHSMINFO_MSG
    rhui_info = _RHUIINFO_MSG
    xfs_info = models.XFSPresence()
    storage_info = models.StorageInfo()
    custom_repofiles = []
    files = set()
    fields = [
        'packages',
        'rhsm_info',
        'rhui_info',
        'xfs_info',
        'storage_info',
        'custom_repofiles',
        'files'
    ]

    return namedtuple('TestInData', fields)(
                packages,
                rhsm_info,
                rhui_info,
                xfs_info,
                storage_info,
                custom_repofiles,
                files,
    )


# TODO: come up with additional tests for the main function
@pytest.mark.parametrize(
    "distro,cert_path", [("rhel", _DEFAULT_CERT_PATH), ("centos", None)]
)
def test_perform_ok(monkeypatch, distro, cert_path):
    repoids = ['repoidX', 'repoidY']
    monkeypatch.setattr(userspacegen, '_InputData', mocked_consume_data)
    monkeypatch.setattr(userspacegen, '_get_product_certificate_path', lambda: cert_path)
    monkeypatch.setattr(overlaygen, 'create_source_overlay', MockedMountingBase)
    monkeypatch.setattr(userspacegen, '_gather_target_repositories', lambda *x: repoids)
    monkeypatch.setattr(userspacegen, '_create_target_userspace', lambda *x: None)
    monkeypatch.setattr(userspacegen, 'setup_target_rhui_access_if_needed', lambda *x: None)
    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked(release_id=distro))
    monkeypatch.setattr(userspacegen.api, 'produce', produce_mocked())
    monkeypatch.setattr(repofileutils, 'get_repodirs', lambda: ['/etc/yum.repos.d'])

    userspacegen.perform()

    msg_target_repos = models.UsedTargetRepositories(
        repos=[models.UsedTargetRepository(repoid=repo) for repo in repoids])

    assert userspacegen.api.produce.called == 3
    assert isinstance(userspacegen.api.produce.model_instances[0], models.TMPTargetRepositoriesFacts)
    assert userspacegen.api.produce.model_instances[1] == msg_target_repos
    # this one is full of constants, so it's safe to check just the instance
    assert isinstance(userspacegen.api.produce.model_instances[2], models.TargetUserSpaceInfo)


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
        raise CalledProcessError("Command failed with exit code 1", cmd, 1)


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

    out = userspacegen._get_files_owned_by_rpms(context, '/some/path', recursive=False)
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

    out = userspacegen._get_files_owned_by_rpms(context, search_dir, recursive=True)
    # any directory-hash directory should be skipped
    assert sorted(owned[0:4]) == sorted(out)

    def has_dbgmsg(substr):
        return any([substr in log for log in logger.dbgmsg])

    # test a few
    assert has_dbgmsg(
        "SKIP files in the /base/dir/etc/pki/ca-trust/extracted/pem/directory-hash directory:"
        " Not important for the IPU.",
    )
    assert has_dbgmsg('SKIP the tls/certs/server.crt file: not owned by any rpm')
    assert has_dbgmsg('Found the file owned by an rpm: rpm-gpg/RPM-GPG-KEY-2.')


def test_writing_stream_varfile(monkeypatch):

    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(userspacegen, 'get_target_major_version', lambda: '10')

    with tempfile.NamedTemporaryFile(mode='w+') as tmpf:
        tmpf.write('incorrect-stream-value\n')
        tmpf.flush()
        userspacegen.adjust_dnf_stream_variable(MockedMountingBase, tmpf.name)
        tmpf.seek(0)
        content = tmpf.read()

    assert content == '10-stream\n'


def test_failing_stream_varfile_write(monkeypatch):
    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(userspacegen, 'get_target_major_version', lambda: '10')
    with pytest.raises(StopActorExecutionError) as err:
        userspacegen.adjust_dnf_stream_variable(MockedMountingBase, '/path/not/exists')

    assert 'Failed to adjust dnf variable' in str(err.value)


@pytest.mark.parametrize("distro,should_adjust", [('rhel', False), ('centos', True)])
def test_if_adjust_dnf_stream_variable_only_for_centos(monkeypatch, distro, should_adjust):

    def do_nothing(*args, **kwargs):
        pass

    def mock_adjust_stream_variable(context, varfile='/etc/dnf/vars/stream'):
        assert varfile == '/etc/dnf/vars/stream'
        nonlocal adjust_called
        adjust_called = True

    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked(release_id=distro))
    monkeypatch.setattr(userspacegen, 'get_target_major_version', lambda: '10')
    monkeypatch.setattr(rhsm, 'set_container_mode', do_nothing)
    monkeypatch.setattr(rhsm, 'switch_certificate', do_nothing)
    monkeypatch.setattr(userspacegen, '_install_custom_repofiles', do_nothing)
    monkeypatch.setattr(userspacegen, 'adjust_dnf_stream_variable', mock_adjust_stream_variable)
    monkeypatch.setattr(userspacegen, 'gather_target_repositories', do_nothing)

    adjust_called = False

    userspacegen._gather_target_repositories(MockedMountingBase, testInData, None)
    assert adjust_called == should_adjust
