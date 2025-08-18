import json
import os

import pytest

from leapp.actors import StopActorExecutionError
from leapp.libraries.common import distro, repofileutils, rhsm
from leapp.libraries.common.config.architecture import ARCH_ACCEPTED, ARCH_ARM64, ARCH_PPC64LE, ARCH_S390X, ARCH_X86_64
from leapp.libraries.common.distro import _get_distro_repofiles, get_distribution_data, get_distro_repoids
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import RepositoryData, RepositoryFile

_RHEL_REPOFILES = ['/etc/yum.repos.d/redhat.repo']
_CENTOS_REPOFILES = [
    "/etc/yum.repos.d/centos.repo", "/etc/yum.repos.d/centos-addons.repo"
]

_CUR_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.parametrize('distro', ['rhel', 'centos'])
def test_get_distribution_data(monkeypatch, distro):
    common_path = os.path.join(_CUR_DIR, "../../files/", 'distro')
    monkeypatch.setattr(
        api,
        "get_common_folder_path",
        lambda folder: common_path
    )
    data_path = os.path.join(common_path, distro, "gpg-signatures.json")

    def exists_mocked(path):
        assert path == data_path
        return True

    monkeypatch.setattr(os.path, 'exists', exists_mocked)
    ret = get_distribution_data(distro)

    with open(data_path) as fp:
        assert ret == json.load(fp)


@pytest.mark.parametrize('distro', ['rhel', 'centos'])
def test_get_distribution_data_not_exists(monkeypatch, distro):
    common_path = os.path.join(_CUR_DIR, "../../files/", 'distro')
    monkeypatch.setattr(
        api,
        "get_common_folder_path",
        lambda folder: common_path
    )
    data_path = os.path.join(common_path, distro, "gpg-signatures.json")

    def exists_mocked(path):
        assert path == data_path
        return False

    monkeypatch.setattr(os.path, 'exists', exists_mocked)

    with pytest.raises(StopActorExecutionError) as err:
        get_distribution_data(distro)
        assert 'Cannot find distribution signature configuration.' in err


def test_get_distro_repofiles(monkeypatch):
    """
    Test the functionality, not the data.
    """
    test_map = {
        'distro1': {
            '8': {
                'repofile1': ARCH_ACCEPTED,
                'repofile2': [ARCH_X86_64],
            },
            '9': {
                'repofile3': ARCH_ACCEPTED,
            },
        },
        'distro2': {
            '8': {},
            '9': {
                'repofile2': [ARCH_X86_64],
                'repofile3': [ARCH_ARM64, ARCH_S390X, ARCH_PPC64LE],
            },
        },
    }
    monkeypatch.setattr(distro, '_DISTRO_REPOFILES_MAP', test_map)

    # mix of all and specific arch
    repofiles = _get_distro_repofiles('distro1', '8', ARCH_X86_64)
    assert repofiles == ['repofile1', 'repofile2']

    # match all but not x86_64
    repofiles = _get_distro_repofiles('distro1', '8', ARCH_ARM64)
    assert repofiles == ['repofile1']

    repofiles = _get_distro_repofiles('distro2', '9', ARCH_X86_64)
    assert repofiles == ['repofile2']
    repofiles = _get_distro_repofiles('distro2', '9', ARCH_ARM64)
    assert repofiles == ['repofile3']
    repofiles = _get_distro_repofiles('distro2', '9', ARCH_S390X)
    assert repofiles == ['repofile3']
    repofiles = _get_distro_repofiles('distro2', '9', ARCH_PPC64LE)
    assert repofiles == ['repofile3']

    # version not mapped
    repofiles = _get_distro_repofiles('distro2', '8', ARCH_X86_64)
    assert repofiles is None

    # distro not mapped
    repofiles = _get_distro_repofiles('distro42', '8', ARCH_X86_64)
    assert repofiles is None


def _make_repo(repoid):
    return RepositoryData(repoid=repoid, name='name {}'.format(repoid))


def _make_repofile(rfile, data=None):
    if data is None:
        data = [_make_repo("{}-{}".format(rfile.split("/")[-1], i)) for i in range(3)]
    return RepositoryFile(file=rfile, data=data)


def _make_repofiles(rfiles):
    return [_make_repofile(rfile) for rfile in rfiles]


@pytest.mark.parametrize('other_rfiles', [
    [],
    [_make_repofile("foo")],
    _make_repofiles(["foo", "bar"]),
])
@pytest.mark.parametrize(
    "distro_id,skip_rhsm,distro_rfiles",
    [
        ("rhel", True, []),
        ("rhel", True, _make_repofiles(_RHEL_REPOFILES)),
        ("rhel", False, _make_repofiles(_RHEL_REPOFILES)),
        ("centos", True, []),
        ("centos", True, _make_repofiles(_CENTOS_REPOFILES)),
    ]
)
def test_get_distro_repoids(
    monkeypatch, distro_id, skip_rhsm, distro_rfiles, other_rfiles
):
    """
    Tests that the correct repoids are returned

    This is a little ugly because on RHEL the get_distro_repoids function still
    delegates to rhsm.get_available_repo_ids and also has different behavior
    with skip_rhsm
    """
    current_actor = CurrentActorMocked(release_id=distro_id if distro_id else 'rhel')
    monkeypatch.setattr(api, 'current_actor', current_actor)
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: skip_rhsm)

    repofiles = other_rfiles
    if distro_rfiles:
        repofiles.extend(distro_rfiles)
    monkeypatch.setattr(repofileutils, 'get_parsed_repofiles', lambda x: repofiles)

    distro_repoids = []
    for rfile in distro_rfiles:
        distro_repoids.extend([repo.repoid for repo in rfile.data] if rfile else [])
    distro_repoids.sort()

    monkeypatch.setattr(rhsm, 'get_available_repo_ids', lambda _: distro_repoids)
    monkeypatch.setattr(os.path, 'exists', lambda f: f in _CENTOS_REPOFILES)

    class MockedContext:
        @staticmethod
        def full_path(path):
            return path

    repoids = get_distro_repoids(MockedContext(), distro_id, '9', 'x86_64')

    if distro_id == 'rhel' and skip_rhsm:
        assert repoids == []
    else:
        assert sorted(repoids) == distro_repoids


@pytest.mark.parametrize('other_rfiles', [
    [],
    [_make_repofile("foo")],
    _make_repofiles(["foo", "bar"]),
])
def test_get_distro_repoids_no_distro_repofiles(monkeypatch, other_rfiles):
    """
    Test that exception is thrown when there are no known distro provided repofiles.
    """

    def mocked_get_distro_repofiles(*args):
        return []

    monkeypatch.setattr(distro, '_get_distro_repofiles',  mocked_get_distro_repofiles)
    monkeypatch.setattr(repofileutils, "get_parsed_repofiles", lambda x: other_rfiles)

    with pytest.raises(StopActorExecutionError):
        get_distro_repoids(None, 'somedistro', '8', 'x86_64')
