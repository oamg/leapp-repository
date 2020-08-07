# TODO [azhukov] check the consistency of unit tests
import pytest

from leapp import reporting
from leapp.libraries.actor import excluderepositories
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    CustomTargetRepository,
    EnvVar,
    RepositoriesBlacklisted,
    RepositoriesExcluded,
    RepositoriesFacts,
    RepositoriesMap,
    RepositoryData,
    RepositoryFile,
    RepositoryMap,
)


# TODO [azhukov] redesign test. Probably use current_actor_context fixture
@pytest.mark.skip(reason='The test should be redesigned. Now it fails due to '
                         'multiple messages consumed. Mocking api.consume '
                         'not working in this case.')
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
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        envars={'LEAPP_DEVEL_SOURCE_PRODUCT_TYPE': product_type}))
    optionals = set(excluderepositories._get_optional_repo_mapping())
    assert {valid_opt_repoid} == optionals
    assert not non_opt_repoids & optionals


# TODO [azhukov] redesign test. Probably use current_actor_context fixture
@pytest.mark.skip(reason='The test should be redesigned. Now it fails due to '
                         'multiple messages consumed. Mocking api.consume '
                         'not working in this case.')
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
    assert not excluderepositories._get_optional_repo_mapping()


# TODO [azhukov] redesign test. Probably use current_actor_context fixture
@pytest.mark.skip(reason='The test should be redesigned. Now it fails due to '
                         'multiple messages consumed. Mocking api.consume '
                         'not working in this case.')
def test_with_empty_optional_repo(monkeypatch):
    def repositories_mock(*model):
        repos_data = [RepositoryData(repoid='rhel-7-optional-rpms', name='RHEL 7 Server', enabled=False)]
        repos_files = [RepositoryFile(file='/etc/yum.repos.d/redhat.repo', data=repos_data)]
        yield RepositoriesFacts(repositories=repos_files)

    monkeypatch.setattr(excluderepositories, "_get_optional_repo_mapping", lambda: {})
    monkeypatch.setattr(api, "consume", repositories_mock)
    assert not excluderepositories._get_repos_to_exclude()


# TODO [azhukov] redesign test. Probably use current_actor_context fixture
@pytest.mark.skip(reason='The test should be redesigned. Now it fails due to '
                         'multiple messages consumed. Mocking api.consume '
                         'not working in this case.')
def test_with_repo_disabled(monkeypatch):
    def repositories_mock(*model):
        repos_data = [RepositoryData(repoid='rhel-7-optional-rpms', name='RHEL 7 Server', enabled=False)]
        repos_files = [RepositoryFile(file='/etc/yum.repos.d/redhat.repo', data=repos_data)]
        yield RepositoriesFacts(repositories=repos_files)

    monkeypatch.setattr(excluderepositories, "_get_optional_repo_mapping",
                        lambda: {'rhel-7-optional-rpms': 'rhel-7'})
    monkeypatch.setattr(api, "consume", repositories_mock)
    disabled = excluderepositories._get_repos_to_exclude()
    assert 'rhel-7' in disabled


# TODO [azhukov] redesign test. Probably use current_actor_context fixture
@pytest.mark.skip(reason='The test should be redesigned. Now it fails due to '
                         'multiple messages consumed. Mocking api.consume '
                         'not working in this case.')
def test_with_repo_enabled(monkeypatch):
    def repositories_mock(*model):
        repos_data = [RepositoryData(repoid='rhel-7-optional-rpms', name='RHEL 7 Server')]
        repos_files = [RepositoryFile(file='/etc/yum.repos.d/redhat.repo', data=repos_data)]
        yield RepositoriesFacts(repositories=repos_files)

    monkeypatch.setattr(excluderepositories, "_get_optional_repo_mapping",
                        lambda: {'rhel-7-optional-rpms': 'rhel-7'})
    monkeypatch.setattr(api, "consume", repositories_mock)
    assert not excluderepositories._get_repos_to_exclude()


def test_repositoriesexcluded_not_empty(monkeypatch):
    name = 'test'
    monkeypatch.setattr(excluderepositories, "_get_repos_to_exclude", lambda: [name])
    monkeypatch.setattr(api, "produce", produce_mocked())
    monkeypatch.setattr(reporting, "create_report", produce_mocked())

    excluderepositories.process()
    assert api.produce.called == 2
    assert isinstance(api.produce.model_instances[0], RepositoriesExcluded)
    assert isinstance(api.produce.model_instances[1], RepositoriesBlacklisted)
    assert api.produce.model_instances[0].repoids[0] == name
    assert reporting.create_report.called == 1


def test_repositoriesblacklist_empty(monkeypatch):
    monkeypatch.setattr(excluderepositories, "_get_repos_to_exclude", lambda: [])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, "produce", produce_mocked())

    excluderepositories.process()
    assert api.produce.called == 0


@pytest.mark.parametrize(
    ("enabled_repo", "exp_len_of_messages"),
    [
        ("codeready-builder-for-rhel-8-x86_64-rpms", 1),
        ("some_other_enabled_repo", 3),
        (None, 3),
    ],
)
def test_enablerepo_option(
    current_actor_context, monkeypatch, enabled_repo, exp_len_of_messages
):
    monkeypatch.setattr(
        excluderepositories, "get_product_type", lambda x: "ga"
    )

    if enabled_repo:
        current_actor_context.feed(CustomTargetRepository(repoid=enabled_repo))

    repos_data = [
        RepositoryData(
            repoid="rhel-7-server-optional-rpms",
            name="RHEL 7 Server",
            enabled=False,
        )
    ]
    repos_files = [
        RepositoryFile(file="/etc/yum.repos.d/redhat.repo", data=repos_data)
    ]
    current_actor_context.feed(RepositoriesFacts(repositories=repos_files))

    current_actor_context.feed(
        RepositoriesMap(
            repositories=(
                [
                    RepositoryMap(
                        to_pes_repo="rhel-7-server-optional-rpms",
                        from_repoid="rhel-7-server-optional-rpms",
                        to_repoid="codeready-builder-for-rhel-8-x86_64-rpms",
                        from_minor_version="all",
                        to_minor_version="all",
                        arch="x86_64",
                        repo_type="rpm",
                    ),
                ]
            )
        )
    )

    current_actor_context.run()
    assert len(current_actor_context.messages()) == exp_len_of_messages
