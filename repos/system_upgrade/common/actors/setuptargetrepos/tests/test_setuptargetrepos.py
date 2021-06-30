from leapp.libraries import stdlib
from leapp.models import CustomTargetRepository, TargetRepositories, RepositoryData, \
    RepositoryFile, RepositoriesFacts, RepositoryMap, RepositoriesMap, RepositoriesSetupTasks, \
    RepositoriesBlacklisted


def test_minimal_execution(current_actor_context):
    current_actor_context.run()


def test_custom_repos(current_actor_context):
    custom = CustomTargetRepository(repoid='rhel-8-server-rpms',
                                    name='RHEL 8 Server (RPMs)',
                                    baseurl='https://.../dist/rhel/server/8/os',
                                    enabled=True)

    blacklisted = CustomTargetRepository(repoid='rhel-8-blacklisted-rpms',
                                         name='RHEL 8 Blacklisted (RPMs)',
                                         baseurl='https://.../dist/rhel/blacklisted/8/os',
                                         enabled=True)

    repos_blacklisted = RepositoriesBlacklisted(repoids=['rhel-8-blacklisted-rpms'])

    current_actor_context.feed(custom)
    current_actor_context.feed(blacklisted)
    current_actor_context.feed(repos_blacklisted)
    current_actor_context.run()

    assert current_actor_context.consume(TargetRepositories)

    custom_repos = current_actor_context.consume(TargetRepositories)[0].custom_repos
    assert len(custom_repos) == 1
    assert custom_repos[0].repoid == 'rhel-8-server-rpms'


def test_repositories_setup_tasks(current_actor_context):
    repositories_setup_tasks = RepositoriesSetupTasks(to_enable=['rhel-8-server-rpms',
                                                                 'rhel-8-blacklisted-rpms'])

    repos_blacklisted = RepositoriesBlacklisted(repoids=['rhel-8-blacklisted-rpms'])

    current_actor_context.feed(repositories_setup_tasks)
    current_actor_context.feed(repos_blacklisted)
    current_actor_context.run()
    assert current_actor_context.consume(TargetRepositories)

    rhel_repos = current_actor_context.consume(TargetRepositories)[0].rhel_repos
    assert len(rhel_repos) == 1
    assert rhel_repos[0].repoid == 'rhel-8-server-rpms'


def test_repos_mapping(current_actor_context):
    repos_data = [
        RepositoryData(repoid='rhel-7-server-rpms', name='RHEL 7 Server'),
        RepositoryData(repoid='rhel-7-blacklisted-rpms', name='RHEL 7 Blacklisted')]
    repos_files = [RepositoryFile(file='/etc/yum.repos.d/redhat.repo', data=repos_data)]
    facts = RepositoriesFacts(repositories=repos_files)
    arch = stdlib.run(['uname', '-m'])['stdout'].strip()

    mapping = [RepositoryMap(from_repoid='rhel-7-server-rpms',
                             to_repoid='rhel-8-for-{}-baseos-htb-rpms'.format(arch),
                             to_pes_repo='rhel8-baseos',
                             from_minor_version='all',
                             to_minor_version='all',
                             arch=arch,
                             repo_type='rpm'),
               RepositoryMap(from_repoid='rhel-7-server-rpms',
                             to_repoid='rhel-8-for-{}-appstream-htb-rpms'.format(arch),
                             to_pes_repo='rhel8-appstream',
                             from_minor_version='all',
                             to_minor_version='all',
                             arch=arch,
                             repo_type='rpm'),
               RepositoryMap(from_repoid='rhel-7-blacklist-rpms',
                             to_repoid='rhel-8-blacklist-rpms',
                             to_pes_repo='rhel8-blacklist',
                             from_minor_version='all',
                             to_minor_version='all',
                             arch=arch,
                             repo_type='rpm')]
    repos_map = RepositoriesMap(repositories=mapping)

    repos_blacklisted = RepositoriesBlacklisted(repoids=['rhel-8-blacklisted-rpms'])

    current_actor_context.feed(facts)
    current_actor_context.feed(repos_map)
    current_actor_context.feed(repos_blacklisted)
    current_actor_context.run()
    assert current_actor_context.consume(TargetRepositories)

    rhel_repos = current_actor_context.consume(TargetRepositories)[0].rhel_repos
    assert len(rhel_repos) == 2
    assert {repo.repoid for repo in rhel_repos} == {'rhel-8-for-x86_64-baseos-htb-rpms',
                                                    'rhel-8-for-x86_64-appstream-htb-rpms'}
