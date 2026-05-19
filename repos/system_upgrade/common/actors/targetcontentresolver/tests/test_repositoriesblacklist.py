import pytest

from leapp import reporting
from leapp.libraries.actor import repositoriesblacklist
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    CustomTargetRepository,
    PESIDRepositoryEntry,
    RepoMapEntry,
    RepositoriesFacts,
    RepositoriesMapping,
    RepositoryData,
    RepositoryFile
)


@pytest.fixture
def repofacts_opts_disabled():
    repos_data = [
        RepositoryData(
            repoid="codeready-builder-for-rhel-8-x86_64-rpms",
            name="RHEL 8 CRB",
            enabled=False,
        )
    ]
    repos_files = [
        RepositoryFile(file="/etc/yum.repos.d/redhat.repo", data=repos_data)
    ]
    return RepositoriesFacts(repositories=repos_files)


@pytest.fixture
def rhel8_crb_pesidrepo():
    return PESIDRepositoryEntry(
        pesid='rhel8-CRB',
        major_version='8',
        repoid='codeready-builder-for-rhel-8-x86_64-rpms',
        rhui='',
        arch='x86_64',
        channel='ga',
        repo_type='rpm',
        distro='rhel',
    )


@pytest.fixture
def rhel9_crb_pesidrepo():
    return PESIDRepositoryEntry(
        pesid='rhel9-CRB',
        major_version='9',
        repoid='codeready-builder-for-rhel-9-x86_64-rpms',
        rhui='',
        arch='x86_64',
        channel='ga',
        repo_type='rpm',
        distro='rhel',
    )


@pytest.fixture
def repomap_opts_only(rhel8_crb_pesidrepo, rhel9_crb_pesidrepo):
    return RepositoriesMapping(
        mapping=[RepoMapEntry(source='rhel8-CRB', target=['rhel9-CRB'])],
        repositories=[rhel8_crb_pesidrepo, rhel9_crb_pesidrepo]
    )


def test_all_target_optionals_blacklisted_when_no_optional_on_source(monkeypatch, repomap_opts_only):
    """
    Tests whether every target optional repository gets blacklisted
    if no optional repositories are used on the source system.
    """

    repos_data = [
        RepositoryData(
            repoid="rhel-8-server-rpms",
            name="RHEL 8 Server",
            enabled=True,
        )
    ]
    repos_files = [
        RepositoryFile(file="/etc/yum.repos.d/redhat.repo", data=repos_data)
    ]
    repo_facts = RepositoriesFacts(repositories=repos_files)

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[repo_facts]))
    monkeypatch.setattr(reporting, 'create_report', produce_mocked())

    result = repositoriesblacklist.process(repomap_opts_only)

    assert 'codeready-builder-for-rhel-9-x86_64-rpms' in result


def test_with_no_mapping_for_optional_repos(monkeypatch, repomap_opts_only, repofacts_opts_disabled):
    """
    Tests whether an empty set is returned if no valid target is found for an optional repository in mapping data.
    """

    repomap_opts_only.repositories[1].pesid = 'test_pesid'

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[repofacts_opts_disabled]))

    result = repositoriesblacklist.process(repomap_opts_only)

    assert not result


def test_blacklist_produced_when_optional_repo_disabled(monkeypatch, repofacts_opts_disabled, repomap_opts_only):
    """
    Tests whether a correct blacklist is generated when there is disabled optional repo on the system.
    """

    monkeypatch.setattr(
        api,
        "current_actor",
        CurrentActorMocked(msgs=[repofacts_opts_disabled]),
    )
    monkeypatch.setattr(reporting, "create_report", produce_mocked())

    result = repositoriesblacklist.process(repomap_opts_only)

    assert result, 'A blacklist should get generated.'

    expected_blacklisted_repoid = 'codeready-builder-for-rhel-9-x86_64-rpms'
    err_msg = 'Blacklist does not contain expected repoid.'
    assert expected_blacklisted_repoid in result, err_msg


def test_no_blacklist_produced_when_optional_repo_enabled(monkeypatch, repofacts_opts_disabled, repomap_opts_only):
    """
    Tests whether an empty set is returned when an optional repository is enabled.

    Data are set up in such a fashion so that the determined blacklist would not be empty.
    """

    repofacts_opts_disabled.repositories[0].data[0].enabled = True

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[repofacts_opts_disabled]))

    result = repositoriesblacklist.process(repomap_opts_only)

    assert not result


def test_repositoriesblacklist_not_empty(monkeypatch, repofacts_opts_disabled, repomap_opts_only):
    """
    Tests whether the correct set of blacklisted repoids is returned.
    """

    blacklisted_repoid = 'test'
    monkeypatch.setattr(repositoriesblacklist, "_get_repoids_to_exclude", lambda dummy_mapping: {blacklisted_repoid})
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[repofacts_opts_disabled]))
    monkeypatch.setattr(reporting, "create_report", produce_mocked())

    result = repositoriesblacklist.process(repomap_opts_only)
    assert blacklisted_repoid in result
    assert reporting.create_report.called == 1


def test_repositoriesblacklist_empty(monkeypatch, repofacts_opts_disabled, repomap_opts_only):
    """
    Tests whether an empty set is returned if there are some disabled optional
    repos, but an empty blacklist is determined from the repo mapping data.
    """

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[repofacts_opts_disabled]))
    monkeypatch.setattr(
        repositoriesblacklist,
        "_get_repoids_to_exclude",
        lambda dummy_mapping: set()
    )

    result = repositoriesblacklist.process(repomap_opts_only)
    assert not result


@pytest.mark.parametrize(
    ("enabled_repo", "exp_report_title", "message_produced"),
    [
        ("codeready-builder-for-rhel-9-x86_64-rpms", "Using repository not supported by Red Hat", False),
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

    msgs_to_feed = [repofacts_opts_disabled]

    if enabled_repo:
        msgs_to_feed.append(CustomTargetRepository(repoid=enabled_repo))
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs_to_feed))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    result = repositoriesblacklist.process(repomap_opts_only)
    assert reporting.create_report.report_fields["title"] == exp_report_title
    if message_produced:
        assert result
    else:
        assert not result
