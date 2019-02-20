from leapp.models import CustomTargetRepository, TargetRepositories, RepositoryData, \
    RepositoryFile, RepositoriesFacts, RepositoryMap, RepositoriesMap


def test_minimal_execution(current_actor_context):
    current_actor_context.run()


def test_custom_repos(current_actor_context):
    custom = CustomTargetRepository(repoid='rhel-8-server-rpms',
                                    name='RHEL 8 Server (RPMs)',
                                    baseurl='https://.../dist/rhel/server/8/os',
                                    enabled=True)
    
    current_actor_context.feed(custom)
    current_actor_context.run()
    assert current_actor_context.consume(TargetRepositories)
    assert len(current_actor_context.consume(TargetRepositories)[0].custom_repos) == 1


def test_repos_mapping(current_actor_context):
    repos_data = [RepositoryData(repoid='rhel-7-server-rpms', name='RHEL 7 Server')]
    repos_files = [RepositoryFile(file='/etc/yum.repos.d/redhat.repo', data=repos_data)]    
    facts = RepositoriesFacts(repositories=repos_files)

    mapping=[RepositoryMap(from_id='rhel-7-server-rpms',
                           to_id='rhel-8-for-x86_64-baseos-htb-rpms',
                           from_minor_version='all',
                           to_minor_version='all',
                           arch='x86_64',
                           repo_type='rpm'),
             RepositoryMap(from_id='rhel-7-server-rpms',
                           to_id='rhel-8-for-x86_64-appstream-htb-rpms',
                           from_minor_version='all',
                           to_minor_version='all',
                           arch='x86_64',
                           repo_type='rpm')]
    repos_map = RepositoriesMap(repositories=mapping)

    current_actor_context.feed(facts)
    current_actor_context.feed(repos_map)
    current_actor_context.run()
    assert current_actor_context.consume(TargetRepositories)
    assert len(current_actor_context.consume(TargetRepositories)[0].rhel_repos) == 2
