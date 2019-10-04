# from leapp.models import RepositoriesBlacklisted, RepositoriesFacts, RepositoryFile, RepositoryData
from leapp.models import RepositoryMap, RepositoriesMap, RepositoriesFacts, RepositoryFile, RepositoryData
from leapp.snactor.fixture import current_actor_context
from leapp.libraries.actor import library


def get_repo_data(repoids, enabled=True):
    data = []
    for repo in repoids:
        data.append(RepositoryData(repoid=repo, name=repo, enabled=enabled))
    return data


def get_repo_files(repoids, enabled=True):
    files = []
    for i, repo in enumerate(repoids):
        files.append(RepositoryFile(file='/etc/yum.d/sample{}.repo'.format(i),
                                    data=get_repo_data([repo])))
    return files


def get_repo_facts(repoids, enabled=True, multiple_files=False):
    if multiple_files:
        repos = get_repo_files(repoids, enabled=enabled)
    else:
        repos = [RepositoryFile(file='/etc/yum.d/sample.repo',
                                data=get_repo_data(repoids, enabled))]
    return RepositoriesFacts(repositories=repos)


def get_optionals_repositories_map():
    mapping = [RepositoryMap(from_id='TEST-rhel-7-server-eus-optional-rpms',
                             to_id='TEST-codeready-builder-for-rhel-8-x86_64-rpms',
                             from_minor_version='all',
                             to_minor_version='all',
                             arch='x86_64',
                             repo_type='rpm'),
               RepositoryMap(from_id='TEST-rhel-7-for-power-le-eus-optional-rpms',
                             to_id='TEST-codeready-builder-for-rhel-8-ppc64le-rpms',
                             from_minor_version='all',
                             to_minor_version='all',
                             arch='ppc64le',
                             repo_type='rpm')]

    return RepositoriesMap(repositories=mapping)


def test_repositoriesblacklist_not_empty(current_actor_context, monkeypatch):
    repos_data = [
        RepositoryData(repoid='rhel-7-server-rpms', name='RHEL 7 Server'),
        RepositoryData(repoid='rhel-7-blacklisted-rpms', name='RHEL 7 Blacklisted')]
    repos_files = [RepositoryFile(file='/etc/yum.repos.d/redhat.repo', data=repos_data)]
    facts = RepositoriesFacts(repositories=repos_files)

    current_actor_context.feed(facts)
    current_actor_context.feed(repos_files)
    current_actor_context.feed(repos_data)
    current_actor_context.feed(get_optionals_repositories_map())
    current_actor_context.run()
    repo_map_list = get_optionals_repositories_map()
    blacklisted_repos = current_actor_context.consume(RepositoriesFacts)

    assert repo_map_list
    assert len(blacklisted_repos) == 2
