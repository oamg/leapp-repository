import pytest

from leapp.libraries import stdlib
from leapp.libraries.actor import setuptargetrepos
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    CustomTargetRepository,
    InstalledRPM,
    PESIDRepositoryEntry,
    RepoMapEntry,
    RepositoriesBlacklisted,
    RepositoriesFacts,
    RepositoriesMapping,
    RepositoriesSetupTasks,
    RepositoryData,
    RepositoryFile,
    RPM,
    TargetRepositories
)

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


def mock_package(pkg_name, repository=None):
    return RPM(name=pkg_name, version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
               pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51', repository=repository)


def test_minimal_execution(monkeypatch):
    """
    Tests whether the actor does not fail if no messages except the RepositoriesMapping are provided.
    """
    msgs = [
        RepositoriesMapping(mapping=[], repositories=[])
    ]

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    setuptargetrepos.process()


def test_custom_repos(monkeypatch):
    """
    Tests whether the CustomRepos provided to the actor are propagated to the TargetRepositories after
    blacklist filtering is applied on them.
    """
    custom = CustomTargetRepository(repoid='rhel-8-server-rpms',
                                    name='RHEL 8 Server (RPMs)',
                                    baseurl='https://.../dist/rhel/server/8/os',
                                    enabled=True)

    blacklisted = CustomTargetRepository(repoid='rhel-8-blacklisted-rpms',
                                         name='RHEL 8 Blacklisted (RPMs)',
                                         baseurl='https://.../dist/rhel/blacklisted/8/os',
                                         enabled=True)

    repos_blacklisted = RepositoriesBlacklisted(repoids=['rhel-8-blacklisted-rpms'])

    repositories_mapping = RepositoriesMapping(
        mapping=[],
        repositories=[]
    )

    msgs = [custom, blacklisted, repos_blacklisted, repositories_mapping]

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    setuptargetrepos.process()

    assert api.produce.called

    custom_repos = api.produce.model_instances[0].custom_repos
    assert len(custom_repos) == 1
    assert custom_repos[0].repoid == 'rhel-8-server-rpms'


def test_repositories_setup_tasks(monkeypatch):
    """
    Tests whether the actor propagates repositories received via a RepositoriesSetupTasks message
    to the resulting TargetRepositories (and blacklist filtering is applied to them).
    """
    repositories_setup_tasks = RepositoriesSetupTasks(to_enable=['rhel-8-server-rpms',
                                                                 'rhel-8-blacklisted-rpms'])
    repos_blacklisted = RepositoriesBlacklisted(repoids=['rhel-8-blacklisted-rpms'])
    repositories_mapping = RepositoriesMapping(mapping=[], repositories=[])
    msgs = [repositories_setup_tasks, repos_blacklisted, repositories_mapping]

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    setuptargetrepos.process()

    assert api.produce.called

    rhel_repos = api.produce.model_instances[0].rhel_repos
    assert len(rhel_repos) == 1
    assert rhel_repos[0].repoid == 'rhel-8-server-rpms'


def test_repos_mapping(monkeypatch):
    """
    Tests whether actor correctly determines what repositories should be enabled on target based
    on the information about what repositories are enabled on the source system using
    the RepositoriesMapping information.
    """
    repos_data = [
        RepositoryData(repoid='rhel-7-server-rpms', name='RHEL 7 Server'),
        RepositoryData(repoid='rhel-7-blacklisted-rpms', name='RHEL 7 Blacklisted')]

    repos_files = [RepositoryFile(file='/etc/yum.repos.d/redhat.repo', data=repos_data)]
    facts = RepositoriesFacts(repositories=repos_files)
    installed_rpms = InstalledRPM(
        items=[mock_package('foreman', 'rhel-7-for-x86_64-satellite-extras-rpms'),
               mock_package('foreman-proxy', 'nosuch-rhel-7-for-x86_64-satellite-extras-rpms')])

    repomap = RepositoriesMapping(
        mapping=[RepoMapEntry(source='rhel7-base', target=['rhel8-baseos', 'rhel8-appstream', 'rhel8-blacklist']),
                 RepoMapEntry(source='rhel7-satellite-extras', target=['rhel8-satellite-extras'])],
        repositories=[
            PESIDRepositoryEntry(
                pesid='rhel7-base',
                repoid='rhel-7-server-rpms',
                major_version='7',
                arch='x86_64',
                repo_type='rpm',
                channel='ga',
                rhui=''
            ),
            PESIDRepositoryEntry(
                pesid='rhel8-baseos',
                repoid='rhel-8-for-x86_64-baseos-htb-rpms',
                major_version='8',
                arch='x86_64',
                repo_type='rpm',
                channel='ga',
                rhui=''
            ),
            PESIDRepositoryEntry(
                pesid='rhel8-appstream',
                repoid='rhel-8-for-x86_64-appstream-htb-rpms',
                major_version='8',
                arch='x86_64',
                repo_type='rpm',
                channel='ga',
                rhui=''
            ),
            PESIDRepositoryEntry(
                pesid='rhel8-blacklist',
                repoid='rhel-8-blacklisted-rpms',
                major_version='8',
                arch='x86_64',
                repo_type='rpm',
                channel='ga',
                rhui=''
            ),
            PESIDRepositoryEntry(
                pesid='rhel7-satellite-extras',
                repoid='rhel-7-for-x86_64-satellite-extras-rpms',
                major_version='7',
                arch='x86_64',
                repo_type='rpm',
                channel='ga',
                rhui=''
            ),
            PESIDRepositoryEntry(
                pesid='rhel8-satellite-extras',
                repoid='rhel-8-for-x86_64-satellite-extras-rpms',
                major_version='8',
                arch='x86_64',
                repo_type='rpm',
                channel='ga',
                rhui=''
            ),
        ]
    )

    repos_blacklisted = RepositoriesBlacklisted(repoids=['rhel-8-blacklisted-rpms'])

    msgs = [facts, repomap, repos_blacklisted, installed_rpms]

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    setuptargetrepos.process()
    assert api.produce.called

    rhel_repos = api.produce.model_instances[0].rhel_repos
    assert len(rhel_repos) == 3

    produced_rhel_repoids = {repo.repoid for repo in rhel_repos}
    expected_rhel_repoids = {'rhel-8-for-x86_64-baseos-htb-rpms', 'rhel-8-for-x86_64-appstream-htb-rpms',
                             'rhel-8-for-x86_64-satellite-extras-rpms'}
    assert produced_rhel_repoids == expected_rhel_repoids
