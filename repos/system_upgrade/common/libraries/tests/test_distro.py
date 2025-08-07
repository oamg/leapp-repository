import pytest

from leapp.libraries.common.distro import (
    get_distro_repofiles,
    get_distro_repoids,
)
from leapp.libraries.common import repofileutils, rhsm
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import RepositoryData, RepositoryFile

_RHEL_REPOFILES = ['/etc/yum.repos.d/redhat.repo']
_CENTOS_REPOFILES = [
    "/etc/yum.repos.d/centos.repo", "/etc/yum.repos.d/centos-addons.repo"
]


@pytest.mark.parametrize(
    "distro,expect",
    [
        (None, _RHEL_REPOFILES),
        ("rhel", _RHEL_REPOFILES),
        ("centos", _CENTOS_REPOFILES),
    ],
)
def test_get_distro_repofiles(monkeypatch, distro, expect):
    current_actor = CurrentActorMocked(release_id=distro if distro else 'rhel')
    monkeypatch.setattr(api, 'current_actor', current_actor)

    repofiles = get_distro_repofiles(distro)

    assert sorted(repofiles) == sorted(expect)


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
    "distro,skip_rhsm,distro_rfiles",
    [
        (None, False, _make_repofiles(_RHEL_REPOFILES)),
        ("rhel", True, []),
        ("rhel", True, _make_repofiles(_RHEL_REPOFILES)),
        ("rhel", False, _make_repofiles(_RHEL_REPOFILES)),
        ("centos", True, []),
        ("centos", True, _make_repofiles(_CENTOS_REPOFILES)),
    ]
)
def test_get_distro_repoids(
    monkeypatch, distro, skip_rhsm, distro_rfiles, other_rfiles
):
    """
    Tests that the correct repoids are returned

    This is a little ugly because on RHEL the get_distro_repoids function still
    delegates to rhsm.get_available_repo_ids and also has different behavior
    with skip_rhsm
    """
    current_actor = CurrentActorMocked(release_id=distro if distro else 'rhel')
    monkeypatch.setattr(api, 'current_actor', current_actor)
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: skip_rhsm)

    repos = other_rfiles
    if distro_rfiles:
        repos.extend(distro_rfiles)
    monkeypatch.setattr(repofileutils, 'get_parsed_repofiles', lambda x: repos)

    distro_repoids = []
    for rfile in distro_rfiles:
        distro_repoids.extend([repo.repoid for repo in rfile.data] if rfile else [])
    distro_repoids.sort()

    monkeypatch.setattr(rhsm, 'get_available_repo_ids', lambda _: distro_repoids)

    repoids = get_distro_repoids(None, distro)

    if distro == 'rhel' and skip_rhsm:
        assert repoids == []
    else:
        assert sorted(repoids) == distro_repoids
