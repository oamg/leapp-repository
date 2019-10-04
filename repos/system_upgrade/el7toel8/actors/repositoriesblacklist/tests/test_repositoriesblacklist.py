# from leapp.models import RepositoriesBlacklisted, RepositoriesFacts, RepositoryFile, RepositoryData
from leapp.libraries.actor import library
from leapp.libraries.common.testutils import produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    RepositoriesBlacklisted,
    RepositoriesFacts,
    RepositoriesMap,
    RepositoryMap,
    RepositoryFile,
    RepositoryData,
)
from leapp.snactor.fixture import current_actor_context


def test_repositoriesblacklist_not_empty(current_actor_context, monkeypatch):
    def repositories_mock(*model):
        if model[0].__name__ == 'RepositoriesMap':
            mapping = [
                RepositoryMap(
                    from_id='rhel-7-optional-rpms',
                    to_id='rhel-8-for-x86_64-appstream-htb-rpms',
                    from_minor_version='all',
                    to_minor_version='all',
                    arch='x86_64',
                    repo_type='rpm',
                ),
                RepositoryMap(
                    from_id='rhel-7-blacklist-rpms',
                    to_id='rhel-8-blacklist-rpms',
                    from_minor_version='all',
                    to_minor_version='all',
                    arch='x86_64',
                    repo_type='rpm',
                ),
            ]
            yield RepositoriesMap(repositories=mapping)
        if model[0].__name__ == 'RepositoriesFacts':
            repos_data = [
                RepositoryData(repoid='rhel-7-optional-rpms', name='RHEL 7 Server', enabled=False),
                RepositoryData(repoid='rhel-7-blacklisted-rpms', name='RHEL 7 Blacklisted'),
            ]
            repos_files = [RepositoryFile(file='/etc/yum.repos.d/redhat.repo', data=repos_data)]
            yield RepositoriesFacts(repositories=repos_files)

    monkeypatch.setattr(api, "consume", repositories_mock)
    monkeypatch.setattr(api, "produce", produce_mocked())

    library.process()
    assert api.produce.called == 1
