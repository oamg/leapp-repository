from leapp.models import RepositoriesBlacklisted, RepositoriesFacts, RepositoryFile, RepositoryData
from leapp.snactor.fixture import current_actor_context


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


def test_repositoriesblacklist_empty(current_actor_context):
    current_actor_context.feed()
    current_actor_context.run()
    assert current_actor_context.consume(RepositoriesBlacklisted)
    repoids = current_actor_context.consume(RepositoriesBlacklisted)[0].repoids
    assert 'codeready-builder-for-rhel-8-x86_64-rpms' in repoids


def test_repositoriesblacklist_no_optional(current_actor_context):
    repo_facts = get_repo_facts(['rhel-7-server-rpms', 'rhel-7-extras-rpms'])
    current_actor_context.feed(repo_facts)
    current_actor_context.run()
    assert current_actor_context.consume(RepositoriesBlacklisted)
    repoids = current_actor_context.consume(RepositoriesBlacklisted)[0].repoids
    assert 'codeready-builder-for-rhel-8-x86_64-rpms' in repoids


def test_repositoriesblacklist_disabled_optional(current_actor_context):
    repo_facts = get_repo_facts(['rhel-7-server-optional-rpms'], False)
    current_actor_context.feed(repo_facts)
    current_actor_context.run()
    assert current_actor_context.consume(RepositoriesBlacklisted)
    repoids = current_actor_context.consume(RepositoriesBlacklisted)[0].repoids
    assert 'codeready-builder-for-rhel-8-x86_64-rpms' in repoids


def test_repositoriesblacklist_optional(current_actor_context):
    repo_facts = get_repo_facts(['test', 'rhel-7-server-optional-rpms', 'rhel-7-server-rpms'])
    current_actor_context.feed(repo_facts)
    current_actor_context.run()
    assert not current_actor_context.consume(RepositoriesBlacklisted)


def test_repositoriesblacklist_optional_multiple_repo_files(current_actor_context):
    repo_facts = get_repo_facts(['test', 'rhel-7-server-optional-rpms', 'rhel-7-server-rpms'], True, True)
    current_actor_context.feed(repo_facts)
    current_actor_context.run()
    assert not current_actor_context.consume(RepositoriesBlacklisted)


def test_repositoriesblacklist_no_optional_multiple_repo_files(current_actor_context):
    repo_facts = get_repo_facts(['rhel-7-server-rpms', 'rhel-7-extras-rpms'], True, True)
    current_actor_context.feed(repo_facts)
    current_actor_context.run()
    assert current_actor_context.consume(RepositoriesBlacklisted)
    repoids = current_actor_context.consume(RepositoriesBlacklisted)[0].repoids
    assert 'codeready-builder-for-rhel-8-x86_64-rpms' in repoids
