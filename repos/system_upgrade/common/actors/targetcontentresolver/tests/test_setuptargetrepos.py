import pytest

from leapp.libraries.actor import setuptargetrepos
from leapp.libraries.actor.repomap_calc import RepoMapDataHandler
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    CustomTargetRepository,
    InstalledRPM,
    PESIDRepositoryEntry,
    RepoMapEntry,
    RepositoriesFacts,
    RepositoriesMapping,
    RepositoryData,
    RepositoryFile,
    RPM
)

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


def mock_package(pkg_name, repository=None):
    return RPM(name=pkg_name, version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
               pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51', repository=repository)


def test_minimal_execution(monkeypatch):
    """
    Tests whether the actor does not fail if no messages except the RepositoriesMapping are provided.
    """
    repos_mapping = RepositoriesMapping(mapping=[], repositories=[])
    msgs = [repos_mapping]

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    setuptargetrepos.setup_target_repos(
        RepoMapDataHandler(repos_mapping),
        enabled_repoids=set(),
        pes_requested_repoids=set(),
        blocklisted_repoids=set(),
        external_repoids_requests=set(),
    )


def test_custom_repos(monkeypatch):
    """
    Tests whether the CustomRepos provided to the actor are propagated to the TargetRepositories after
    blocklist filtering is applied on them.
    """
    custom = CustomTargetRepository(repoid='rhel-8-server-rpms',
                                    name='RHEL 8 Server (RPMs)',
                                    baseurl='https://.../dist/rhel/server/8/os',
                                    enabled=True)

    blocklisted = CustomTargetRepository(repoid='rhel-8-blocklisted-rpms',
                                         name='RHEL 8 Blocklisted (RPMs)',
                                         baseurl='https://.../dist/rhel/blocklisted/8/os',
                                         enabled=True)

    repositories_mapping = RepositoriesMapping(
        mapping=[],
        repositories=[]
    )

    msgs = [custom, blocklisted, repositories_mapping]

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    handler = RepoMapDataHandler(repositories_mapping)
    setuptargetrepos.setup_target_repos(
        handler,
        enabled_repoids=set(),
        pes_requested_repoids=set(),
        blocklisted_repoids={'rhel-8-blocklisted-rpms'},
        external_repoids_requests=set(),
    )

    assert api.produce.called

    custom_repos = api.produce.model_instances[0].custom_repos
    assert len(custom_repos) == 1
    assert custom_repos[0].repoid == 'rhel-8-server-rpms'


def test_repositories_setup_tasks(monkeypatch):
    """
    Tests whether the actor propagates requested repoids
    to the resulting TargetRepositories (and blocklist filtering is applied to them).
    """
    repositories_mapping = RepositoriesMapping(mapping=[], repositories=[])
    msgs = [repositories_mapping]

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    handler = RepoMapDataHandler(repositories_mapping)
    setuptargetrepos.setup_target_repos(
        handler,
        enabled_repoids=set(),
        pes_requested_repoids=set(),
        blocklisted_repoids={'rhel-8-blacklisted-rpms'},
        external_repoids_requests={'rhel-8-server-rpms', 'rhel-8-blacklisted-rpms'},
    )

    assert api.produce.called

    rhel_repos = api.produce.model_instances[0].rhel_repos
    assert len(rhel_repos) == 1
    assert rhel_repos[0].repoid == 'rhel-8-server-rpms'


@pytest.mark.parametrize('src_distro', ['rhel', 'centos', 'almalinux'])
@pytest.mark.parametrize('dst_distro', ['rhel', 'centos', 'almalinux'])
def test_repos_mapping_for_distro(monkeypatch, src_distro, dst_distro):
    """
    Tests whether actor correctly determines what repositories should be enabled on target based
    on the information about what repositories are enabled on the source system using
    the RepositoriesMapping information for a specific source and target distro pair.
    """
    repos_data = [
        RepositoryData(repoid='{}-8-server-rpms'.format(src_distro), name='{} 8 Server'.format(src_distro)),
        RepositoryData(repoid='{}-8-blacklisted-rpms'.format(src_distro), name='{} 8 Blacklisted'.format(src_distro))]

    repos_files = [RepositoryFile(file='/etc/yum.repos.d/redhat.repo', data=repos_data)]
    facts = RepositoriesFacts(repositories=repos_files)
    installed_rpms = InstalledRPM(
        items=[mock_package('foreman', '{}-8-for-x86_64-satellite-extras-rpms'.format(src_distro)),
               mock_package('foreman-proxy', 'nosuch-{}-8-for-x86_64-satellite-extras-rpms'.format(src_distro))])

    repomap = RepositoriesMapping(
        mapping=[RepoMapEntry(source='{0}8-base'.format(src_distro),
                              target=['{0}9-baseos'.format(dst_distro),
                                      '{0}9-appstream'.format(dst_distro),
                                      '{0}9-blacklist'.format(dst_distro)]),
                 RepoMapEntry(source='{0}8-satellite-extras'.format(src_distro),
                              target=['{0}9-satellite-extras'.format(dst_distro)])],
        repositories=[
            PESIDRepositoryEntry(
                pesid='{0}8-base'.format(src_distro),
                repoid='{0}-8-server-rpms'.format(src_distro),
                major_version='8',
                arch='x86_64',
                repo_type='rpm',
                channel='ga',
                rhui='',
                distro=src_distro,
            ),
            PESIDRepositoryEntry(
                pesid='{0}9-baseos'.format(dst_distro),
                repoid='{0}-9-for-x86_64-baseos-htb-rpms'.format(dst_distro),
                major_version='9',
                arch='x86_64',
                repo_type='rpm',
                channel='ga',
                rhui='',
                distro=dst_distro,
            ),
            PESIDRepositoryEntry(
                pesid='{0}9-appstream'.format(dst_distro),
                repoid='{0}-9-for-x86_64-appstream-htb-rpms'.format(dst_distro),
                major_version='9',
                arch='x86_64',
                repo_type='rpm',
                channel='ga',
                rhui='',
                distro=dst_distro,
            ),
            PESIDRepositoryEntry(
                pesid='{0}9-blacklist'.format(dst_distro),
                repoid='{0}-9-blacklisted-rpms'.format(dst_distro),
                major_version='9',
                arch='x86_64',
                repo_type='rpm',
                channel='ga',
                rhui='',
                distro=dst_distro,
            ),
            PESIDRepositoryEntry(
                pesid='{0}8-satellite-extras'.format(src_distro),
                repoid='{0}-8-for-x86_64-satellite-extras-rpms'.format(src_distro),
                major_version='8',
                arch='x86_64',
                repo_type='rpm',
                channel='ga',
                rhui='',
                distro=src_distro,
            ),
            PESIDRepositoryEntry(
                pesid='{0}9-satellite-extras'.format(dst_distro),
                repoid='{0}-9-for-x86_64-satellite-extras-rpms'.format(dst_distro),
                major_version='9',
                arch='x86_64',
                repo_type='rpm',
                channel='ga',
                rhui='',
                distro=dst_distro,
            ),
        ]
    )

    msgs = [facts, repomap, installed_rpms]

    monkeypatch.setattr(
        api,
        'current_actor',
        CurrentActorMocked(msgs=msgs, src_distro=src_distro, dst_distro=dst_distro),
    )
    monkeypatch.setattr(api, 'produce', produce_mocked())

    handler = RepoMapDataHandler(repomap)
    enabled_repoids = {
        '{}-8-server-rpms'.format(src_distro),
        '{}-8-blacklisted-rpms'.format(src_distro),
    }
    setuptargetrepos.setup_target_repos(
        handler,
        enabled_repoids=enabled_repoids,
        pes_requested_repoids=set(),
        blocklisted_repoids={'{}-9-blacklisted-rpms'.format(dst_distro)},
        external_repoids_requests=set(),
    )
    assert api.produce.called

    distro_repos = api.produce.model_instances[0].distro_repos
    rhel_repos = api.produce.model_instances[0].rhel_repos

    assert len(distro_repos) == 3

    produced_distro_repoids = {repo.repoid for repo in distro_repos}
    produced_rhel_repoids = {repo.repoid for repo in rhel_repos}

    expected_repoids = {
        "{0}-9-for-x86_64-baseos-htb-rpms".format(dst_distro),
        "{0}-9-for-x86_64-appstream-htb-rpms".format(dst_distro),
        "{0}-9-for-x86_64-satellite-extras-rpms".format(dst_distro),
    }

    assert produced_distro_repoids == expected_repoids
    if dst_distro == 'rhel':
        assert len(rhel_repos) == 3
        assert produced_rhel_repoids == expected_repoids
    else:
        assert not rhel_repos


def test_pes_requested_repoids_added_to_target(monkeypatch):
    """
    Tests whether PES-requested repoids are added to the target repositories
    and that blocklisted PES-requested repoids are excluded.
    """
    repositories_mapping = RepositoriesMapping(mapping=[], repositories=[])
    msgs = [repositories_mapping]

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    handler = RepoMapDataHandler(repositories_mapping)
    setuptargetrepos.setup_target_repos(
        handler,
        enabled_repoids=set(),
        pes_requested_repoids={'pes-repo-1', 'pes-repo-2', 'pes-blocked'},
        blocklisted_repoids={'pes-blocked'},
        external_repoids_requests=set(),
    )

    assert api.produce.called

    distro_repos = api.produce.model_instances[0].distro_repos
    produced_repoids = {repo.repoid for repo in distro_repos}

    assert 'pes-repo-1' in produced_repoids
    assert 'pes-repo-2' in produced_repoids
    assert 'pes-blocked' not in produced_repoids


def test_pes_and_external_repoids_combined(monkeypatch):
    """
    Tests whether PES-requested and external repoids are combined
    in the final target repositories, with blacklist filtering applied to both.
    """
    repositories_mapping = RepositoriesMapping(mapping=[], repositories=[])
    msgs = [repositories_mapping]

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    handler = RepoMapDataHandler(repositories_mapping)
    setuptargetrepos.setup_target_repos(
        handler,
        enabled_repoids=set(),
        pes_requested_repoids={'pes-repo'},
        blocklisted_repoids={'blocked-repo'},
        external_repoids_requests={'ext-repo', 'blocked-repo'},
    )

    assert api.produce.called

    distro_repos = api.produce.model_instances[0].distro_repos
    produced_repoids = {repo.repoid for repo in distro_repos}

    assert 'pes-repo' in produced_repoids
    assert 'ext-repo' in produced_repoids
    assert 'blocked-repo' not in produced_repoids
