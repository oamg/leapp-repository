import pytest

from leapp import reporting
from leapp.libraries.actor import repositoriesblacklist
from leapp.libraries.common.testutils import (
    CurrentActorMocked,
    create_report_mocked,
    produce_mocked,
)
from leapp.libraries.stdlib import api
from leapp.models import (
    CustomTargetRepository,
    EnvVar,
    RepositoriesBlacklisted,
    RepositoriesFacts,
    RepositoriesMap,
    RepositoryData,
    RepositoryFile,
    RepositoryMap,
)


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
    optionals = set(repositoriesblacklist._get_optional_repo_mapping())
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
    assert not repositoriesblacklist._get_optional_repo_mapping()


def test_with_empty_optional_repo(monkeypatch):
    def repositories_mock(*model):
        repos_data = [RepositoryData(repoid='rhel-7-optional-rpms', name='RHEL 7 Server', enabled=False)]
        repos_files = [RepositoryFile(file='/etc/yum.repos.d/redhat.repo', data=repos_data)]
        yield RepositoriesFacts(repositories=repos_files)

    monkeypatch.setattr(repositoriesblacklist, "_get_optional_repo_mapping", lambda: {})
    monkeypatch.setattr(api, "consume", repositories_mock)
    assert not repositoriesblacklist._get_repos_to_exclude()


def test_with_repo_disabled(monkeypatch):
    def repositories_mock(*model):
        repos_data = [RepositoryData(repoid='rhel-7-optional-rpms', name='RHEL 7 Server', enabled=False)]
        repos_files = [RepositoryFile(file='/etc/yum.repos.d/redhat.repo', data=repos_data)]
        yield RepositoriesFacts(repositories=repos_files)

    monkeypatch.setattr(repositoriesblacklist, "_get_optional_repo_mapping",
                        lambda: {'rhel-7-optional-rpms': 'rhel-7'})
    monkeypatch.setattr(api, "consume", repositories_mock)
    disabled = repositoriesblacklist._get_repos_to_exclude()
    assert 'rhel-7' in disabled


def test_with_repo_enabled(monkeypatch):
    def repositories_mock(*model):
        repos_data = [RepositoryData(repoid='rhel-7-optional-rpms', name='RHEL 7 Server')]
        repos_files = [RepositoryFile(file='/etc/yum.repos.d/redhat.repo', data=repos_data)]
        yield RepositoriesFacts(repositories=repos_files)

    monkeypatch.setattr(repositoriesblacklist, "_get_optional_repo_mapping",
                        lambda: {'rhel-7-optional-rpms': 'rhel-7'})
    monkeypatch.setattr(api, "consume", repositories_mock)
    assert not repositoriesblacklist._get_repos_to_exclude()


def test_repositoriesblacklist_not_empty(monkeypatch):
    name = 'test'
    monkeypatch.setattr(repositoriesblacklist, "_get_repos_to_exclude", lambda: {name})
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, "produce", produce_mocked())
    monkeypatch.setattr(reporting, "create_report", produce_mocked())

    repositoriesblacklist.process()
    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], RepositoriesBlacklisted)
    assert api.produce.model_instances[0].repoids[0] == name
    assert reporting.create_report.called == 1


def test_repositoriesblacklist_empty(monkeypatch):
    monkeypatch.setattr(repositoriesblacklist, "_get_repos_to_exclude", lambda: set())  # pylint:disable=W0108
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, "produce", produce_mocked())

    repositoriesblacklist.process()
    assert api.produce.called == 0


@pytest.mark.parametrize(
    ("enabled_repo", "exp_report_title", "message_produced"),
    [
        ("codeready-builder-for-rhel-8-x86_64-rpms", "Using repository not supported by Red Hat", False),
        ("some_other_enabled_repo", "Excluded RHEL 8 repositories", True),
        (None, "Excluded RHEL 8 repositories", True),
    ],
)
def test_enablerepo_option(monkeypatch, enabled_repo, exp_report_title, message_produced):
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
    msgs_to_feed = [
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
            ),
            RepositoriesFacts(repositories=repos_files),
    ]

    if enabled_repo:
        msgs_to_feed.append(CustomTargetRepository(repoid=enabled_repo))
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs_to_feed))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    repositoriesblacklist.process()
    assert reporting.create_report.report_fields["title"] == exp_report_title
    if message_produced:
        assert isinstance(api.produce.model_instances[0], RepositoriesBlacklisted)
    else:
        assert not api.produce.model_instances
