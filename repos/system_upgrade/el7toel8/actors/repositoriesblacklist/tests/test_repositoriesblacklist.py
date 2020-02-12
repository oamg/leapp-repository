from collections import namedtuple

import pytest

from leapp.libraries.actor import library
from leapp.libraries.common.testutils import produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    EnvVar,
    RepositoriesBlacklisted,
    RepositoriesFacts,
    RepositoriesMap,
    RepositoryData,
    RepositoryFile,
    RepositoryMap,
)
from leapp.snactor.fixture import current_actor_context


class CurrentActorMocked(object):
    def __init__(self, envars=None):
        if envars:
            envarsList = [EnvVar(name=key, value=value) for key, value in envars.items()]
        else:
            envarsList = []
        self.configuration = namedtuple('configuration', ['leapp_env_vars'])(envarsList)

    def __call__(self):
        return self


@pytest.mark.parametrize('valid_opt_repoid,product_type', [
    ('rhel-7-optional-rpms', 'ga'),
    ('rhel-7-optional-beta-rpms', 'beta'),
    ('rhel-7-optional-htb-rpms', 'htb'),
])
def test_with_optionals(monkeypatch, valid_opt_repoid, product_type):
    all_opt_repoids = {'rhel-7-optional-rpms', 'rhel-7-optional-beta-rpms', 'rhel-7-optional-htb-rpms'}
    # set of repos that should not be marked as optionals
    non_opt_repoids = all_opt_repoids - {valid_opt_repoid} | {'rhel-7-blacklist-rpms'}

    def repositories_mock(*model):
        mapping = [
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
        for repoid in all_opt_repoids:
            mapping.append(RepositoryMap(
                to_pes_repo='rhel-7-foobar-rpms',
                from_repoid=repoid,
                to_repoid='rhel-8-optional-rpms',
                from_minor_version='all',
                to_minor_version='all',
                arch='x86_64',
                repo_type='rpm',
            ))
        yield RepositoriesMap(repositories=mapping)

    monkeypatch.setattr(api, "consume", repositories_mock)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked({'LEAPP_DEVEL_SOURCE_PRODUCT_TYPE': product_type}))
    optionals = set(library._get_list_of_optional_repos().keys())
    assert {valid_opt_repoid} == optionals
    assert not non_opt_repoids & optionals


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
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
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
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, "produce", produce_mocked())

    library.process()
    assert api.produce.called == 0
