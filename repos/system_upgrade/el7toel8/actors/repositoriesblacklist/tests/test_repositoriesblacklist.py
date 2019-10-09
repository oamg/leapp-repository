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


def test_with_optionals(monkeypatch):
    def repositories_mock(*model):
        mapping = [
            RepositoryMap(
                to_pes_repo='rhel-7-foobar-rpms',
                from_repoid='rhel-7-optional-rpms',
                to_repoid='rhel-8-optional-rpms',
                from_minor_version='all',
                to_minor_version='all',
                arch='x86_64',
                repo_type='rpm',
            ),
            RepositoryMap(
                to_pes_repo='rhel-7-blacklist-rpms',
                from_repoid='rhel-7-blacklist-rpms',
                to_repoid='rhel-8-blacklist-rpms',
                from_minor_version='all',
                to_minor_version='all',
                arch='x86_64',
                repo_type='rpm',
            ),
        ]
        yield RepositoriesMap(repositories=mapping)

    monkeypatch.setattr(api, "consume", repositories_mock)
    optionals = library._get_list_of_optional_repos()
    assert 'rhel-7-optional-rpms' in optionals
    assert 'rhel-7-blacklist-rpms' not in optionals


def test_without_optionals(monkeypatch):
    def repositories_mock(*model):
        mapping = [
            RepositoryMap(
                to_pes_repo='rhel-7-foobar-rpms',
                from_repoid='rhel-7-foobar-rpms',
                to_repoid='rhel-8-foobar-rpms',
                from_minor_version='all',
                to_minor_version='all',
                arch='x86_64',
                repo_type='rpm',
            ),
            RepositoryMap(
                to_pes_repo='rhel-7-blacklist-rpms',
                from_repoid='rhel-7-blacklist-rpms',
                to_repoid='rhel-8-blacklist-rpms',
                from_minor_version='all',
                to_minor_version='all',
                arch='x86_64',
                repo_type='rpm',
            ),
        ]
        yield RepositoriesMap(repositories=mapping)

    monkeypatch.setattr(api, "consume", repositories_mock)
    assert not library._get_list_of_optional_repos()


def test_with_empty_optional_repo(monkeypatch):
    def repositories_mock(*model):
        repos_data = [RepositoryData(repoid='rhel-7-optional-rpms', name='RHEL 7 Server', enabled=False)]
        repos_files = [RepositoryFile(file='/etc/yum.repos.d/redhat.repo', data=repos_data)]
        yield RepositoriesFacts(repositories=repos_files)

    monkeypatch.setattr(library, "_get_list_of_optional_repos", lambda: {})
    monkeypatch.setattr(api, "consume", repositories_mock)
    assert not library._get_disabled_optional_repo()


def test_with_repo_disabled(monkeypatch):
    def repositories_mock(*model):
        repos_data = [RepositoryData(repoid='rhel-7-optional-rpms', name='RHEL 7 Server', enabled=False)]
        repos_files = [RepositoryFile(file='/etc/yum.repos.d/redhat.repo', data=repos_data)]
        yield RepositoriesFacts(repositories=repos_files)

    monkeypatch.setattr(library, "_get_list_of_optional_repos", lambda: {'rhel-7-optional-rpms': 'rhel-7'})
    monkeypatch.setattr(api, "consume", repositories_mock)
    disabled = library._get_disabled_optional_repo()
    assert 'rhel-7' in disabled


def test_with_repo_enabled(monkeypatch):
    def repositories_mock(*model):
        repos_data = [RepositoryData(repoid='rhel-7-optional-rpms', name='RHEL 7 Server')]
        repos_files = [RepositoryFile(file='/etc/yum.repos.d/redhat.repo', data=repos_data)]
        yield RepositoriesFacts(repositories=repos_files)

    monkeypatch.setattr(library, "_get_list_of_optional_repos", lambda: {'rhel-7-optional-rpms': 'rhel-7'})
    monkeypatch.setattr(api, "consume", repositories_mock)
    assert not library._get_disabled_optional_repo()


def test_repositoriesblacklist_not_empty(monkeypatch):
    name = 'test'
    monkeypatch.setattr(library, "_get_disabled_optional_repo", lambda: [name])
    monkeypatch.setattr(api, "produce", produce_mocked())

    library.process()
    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], RepositoriesBlacklisted)
    assert api.produce.model_instances[0].repoids[0] == name


def test_repositoriesblacklist_empty(monkeypatch):
    monkeypatch.setattr(library, "_get_disabled_optional_repo", lambda: [])
    monkeypatch.setattr(api, "produce", produce_mocked())

    library.process()
    assert api.produce.called == 0
