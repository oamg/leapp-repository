import pytest

from leapp import reporting
from leapp.libraries.actor import repositoriesblacklist
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    CustomTargetRepository,
    EnvVar,
    PESIDRepositoryEntry,
    RepoMapEntry,
    RepositoriesBlacklisted,
    RepositoriesFacts,
    RepositoriesMapping,
    RepositoryData,
    RepositoryFile
)


@pytest.fixture
def repofacts_opts_disabled():
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
    return RepositoriesFacts(repositories=repos_files)


@pytest.fixture
def rhel7_optional_pesidrepo():
    return PESIDRepositoryEntry(
        pesid='rhel7-optional',
        major_version='7',
        repoid='rhel-7-server-optional-rpms',
        rhui='',
        arch='x86_64',
        channel='ga',
        repo_type='rpm',
    )


@pytest.fixture
def rhel8_crb_pesidrepo():
    return PESIDRepositoryEntry(
        pesid='rhel8-CRB',
        major_version='8',
        repoid='codeready-builder-for-rhel-8-x86_64-rpms',
        rhui='',
        arch='x86_64',
        channel='ga',
        repo_type='rpm')


@pytest.fixture
def repomap_opts_only(rhel7_optional_pesidrepo, rhel8_crb_pesidrepo):
    return RepositoriesMapping(
        mapping=[RepoMapEntry(source='rhel7-optional', target=['rhel8-CRB'])],
        repositories=[rhel7_optional_pesidrepo, rhel8_crb_pesidrepo]
    )


def test_all_target_optionals_blacklisted_when_no_optional_on_source(monkeypatch, repomap_opts_only):
    """
    Tests whether every target optional repository gets blacklisted
    if no optional repositories are used on the source system.
    """

    repos_data = [
        RepositoryData(
            repoid="rhel-7-server-rpms",
            name="RHEL 7 Server",
            enabled=True,
        )
    ]
    repos_files = [
        RepositoryFile(file="/etc/yum.repos.d/redhat.repo", data=repos_data)
    ]
    repo_facts = RepositoriesFacts(repositories=repos_files)

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[repo_facts, repomap_opts_only]))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(reporting, 'create_report', produce_mocked())

    repositoriesblacklist.process()

    assert api.produce.called
    assert 'codeready-builder-for-rhel-8-x86_64-rpms' in api.produce.model_instances[0].repoids


def test_with_no_mapping_for_optional_repos(monkeypatch, repomap_opts_only, repofacts_opts_disabled):
    """
    Tests whether nothing gets produced if no valid target is found for an optional repository in mapping data.
    """

    repomap_opts_only.repositories[1].pesid = 'test_pesid'

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[repofacts_opts_disabled, repomap_opts_only]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    repositoriesblacklist.process()

    assert not api.produce.called


def test_blacklist_produced_when_optional_repo_disabled(monkeypatch, repofacts_opts_disabled, repomap_opts_only):
    """
    Tests whether a correct blacklist is generated when there is disabled optional repo on the system.
    """

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[repofacts_opts_disabled, repomap_opts_only]))
    monkeypatch.setattr(api, "produce", produce_mocked())
    monkeypatch.setattr(reporting, "create_report", produce_mocked())

    repositoriesblacklist.process()

    assert api.produce.model_instances, 'A blacklist should get generated.'

    expected_blacklisted_repoid = 'codeready-builder-for-rhel-8-x86_64-rpms'
    err_msg = 'Blacklist does not contain expected repoid.'
    assert expected_blacklisted_repoid in api.produce.model_instances[0].repoids, err_msg


def test_no_blacklist_produced_when_optional_repo_enabled(monkeypatch, repofacts_opts_disabled, repomap_opts_only):
    """
    Tests whether nothing is produced when an optional repository is enabled.

    Data are set up in such a fashion so that the determined blacklist would not be empty.
    """

    repofacts_opts_disabled.repositories[0].data[0].enabled = True

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[repofacts_opts_disabled, repomap_opts_only]))
    monkeypatch.setattr(api, "produce", produce_mocked())
    monkeypatch.setattr(reporting, "create_report", produce_mocked())

    repositoriesblacklist.process()

    assert not api.produce.called


def test_repositoriesblacklist_not_empty(monkeypatch, repofacts_opts_disabled, repomap_opts_only):
    """
    Tests whether a message containing correct packages from the determined blacklist is produced.
    """

    blacklisted_repoid = 'test'
    monkeypatch.setattr(repositoriesblacklist, "_get_repoids_to_exclude", lambda dummy_mapping: {blacklisted_repoid})
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[repofacts_opts_disabled, repomap_opts_only]))
    monkeypatch.setattr(api, "produce", produce_mocked())
    monkeypatch.setattr(reporting, "create_report", produce_mocked())

    repositoriesblacklist.process()
    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], RepositoriesBlacklisted)
    assert api.produce.model_instances[0].repoids[0] == blacklisted_repoid
    assert reporting.create_report.called == 1


def test_repositoriesblacklist_empty(monkeypatch, repofacts_opts_disabled, repomap_opts_only):
    """
    Tests whether nothing is produced if there are some disabled optional repos, but an empty blacklist is determined
    from the repo mapping data.
    """

    msgs_to_feed = [repofacts_opts_disabled, repomap_opts_only]

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs_to_feed))
    monkeypatch.setattr(
        repositoriesblacklist,
        "_get_repoids_to_exclude",
        lambda dummy_mapping: set()
    )  # pylint:disable=W0108
    monkeypatch.setattr(api, "produce", produce_mocked())

    repositoriesblacklist.process()
    assert api.produce.called == 0


@pytest.mark.parametrize(
    ("enabled_repo", "exp_report_title", "message_produced"),
    [
        ("codeready-builder-for-rhel-8-x86_64-rpms", "Using repository not supported by Red Hat", False),
        ("some_other_enabled_repo", "Excluded target system repositories", True),
        (None, "Excluded target system repositories", True),
    ],
)
def test_enablerepo_option(monkeypatch,
                           repofacts_opts_disabled,
                           repomap_opts_only,
                           enabled_repo,
                           exp_report_title,
                           message_produced):
    """
    Tests whether the actor respects CustomTargetRepository messages when constructing the blacklist.
    """

    msgs_to_feed = [repomap_opts_only, repofacts_opts_disabled]

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
