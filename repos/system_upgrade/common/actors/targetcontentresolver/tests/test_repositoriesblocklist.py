import pytest

from leapp import reporting
from leapp.libraries.actor import repositoriesblocklist
from leapp.libraries.actor.repomap_calc import RepoMapDataHandler
from leapp.libraries.actor.targetcontentresolver import ExternalRepoSetupTasks
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import PESIDRepositoryEntry, RepoMapEntry, RepositoriesBlocklisted, RepositoriesMapping

_NO_TASKS = ExternalRepoSetupTasks(to_enable=set(), to_block=set(), custom=set())


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


def test_crb_repos_blocked_when_no_crb_on_source(monkeypatch, repomap_opts_only):
    """
    Target CRB repos are blocklisted when no CRB repository
    is enabled on the source system.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        arch='x86_64', src_ver='8.10', dst_ver='9.6', dst_distro='rhel'
    ))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    handler = RepoMapDataHandler(repomap_opts_only)
    result = repositoriesblocklist._calc_internal_blocklist(
        handler, _NO_TASKS, enabled_repoids={'rhel-8-server-rpms'}
    )

    assert 'codeready-builder-for-rhel-9-x86_64-rpms' in result


def test_empty_result_when_no_crb_pesid_in_mapping(monkeypatch, repomap_opts_only):
    """
    Empty set is returned if no valid CRB target is found in mapping data.
    """
    repomap_opts_only.repositories[1].pesid = 'test_pesid'

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        arch='x86_64', src_ver='8.10', dst_ver='9.6', dst_distro='rhel'
    ))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    handler = RepoMapDataHandler(repomap_opts_only)
    result = repositoriesblocklist._calc_internal_blocklist(
        handler, _NO_TASKS, enabled_repoids=set()
    )

    assert not result


def test_blocklist_generated_when_crb_disabled(monkeypatch, repomap_opts_only):
    """
    Blocklist is generated when CRB repos are disabled on the source system.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        arch='x86_64', src_ver='8.10', dst_ver='9.6', dst_distro='rhel'
    ))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    handler = RepoMapDataHandler(repomap_opts_only)
    result = repositoriesblocklist._calc_internal_blocklist(
        handler, _NO_TASKS, enabled_repoids=set()
    )

    assert result, 'A blocklist should get generated.'

    expected_blocklisted_repoid = 'codeready-builder-for-rhel-9-x86_64-rpms'
    err_msg = 'Blocklist does not contain expected repoid.'
    assert expected_blocklisted_repoid in result, err_msg


def test_no_blocklist_when_crb_enabled_on_source(monkeypatch, repomap_opts_only):
    """
    Empty set is returned when a CRB repository is enabled on the source system.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        arch='x86_64', src_ver='8.10', dst_ver='9.6', dst_distro='rhel'
    ))

    handler = RepoMapDataHandler(repomap_opts_only)
    result = repositoriesblocklist._calc_internal_blocklist(
        handler, _NO_TASKS,
        enabled_repoids={'codeready-builder-for-rhel-8-x86_64-rpms'}
    )

    assert not result


def test_blocklist_not_empty_with_mocked_crb_repos(monkeypatch, repomap_opts_only):
    """
    Non-empty blocklist is returned when _get_crb_repos returns repos to exclude.
    """
    blacklisted_repoid = 'test'
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        arch='x86_64', src_ver='8.10', dst_ver='9.6', dst_distro='rhel'
    ))
    monkeypatch.setattr(
        repositoriesblocklist, '_are_crb_repos_disabled', lambda _m, _e: True
    )
    monkeypatch.setattr(
        repositoriesblocklist, '_get_crb_repos', lambda _m, _v: {blacklisted_repoid}
    )
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    result = repositoriesblocklist._calc_internal_blocklist(
        repomap_opts_only, _NO_TASKS, enabled_repoids=set()
    )
    assert blacklisted_repoid in result
    assert reporting.create_report.called == 1


def test_blocklist_empty_with_mocked_empty_crb_repos(monkeypatch, repomap_opts_only):
    """
    Empty set returned when _get_crb_repos returns no repos, even though
    CRB is disabled on the source.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        arch='x86_64', src_ver='8.10', dst_ver='9.6', dst_distro='rhel'
    ))
    monkeypatch.setattr(
        repositoriesblocklist, '_are_crb_repos_disabled', lambda _m, _e: True
    )
    monkeypatch.setattr(
        repositoriesblocklist, '_get_crb_repos', lambda _m, _v: set()
    )
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    result = repositoriesblocklist._calc_internal_blocklist(
        repomap_opts_only, _NO_TASKS, enabled_repoids=set()
    )
    assert not result


@pytest.mark.parametrize(
    ('custom_repoids', 'exp_report_title', 'exp_blocklist_empty'),
    [
        (
            {'codeready-builder-for-rhel-9-x86_64-rpms'},
            None,
            True,
        ),
        (
            {'some_other_enabled_repo'},
            'Excluded target system repositories',
            False,
        ),
        (
            set(),
            'Excluded target system repositories',
            False,
        ),
    ],
)
def test_custom_enablerepo_effect(monkeypatch, repomap_opts_only,
                                  custom_repoids, exp_report_title,
                                  exp_blocklist_empty):
    """
    When a CRB repo is in external_tasks.custom the blocklist is empty.
    When custom contains only non-CRB repos or is empty, CRB repos are excluded and reported.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        arch='x86_64', src_ver='8.10', dst_ver='9.6', dst_distro='rhel'
    ))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    external_tasks = ExternalRepoSetupTasks(
        to_enable=set(), to_block=set(), custom=custom_repoids
    )

    handler = RepoMapDataHandler(repomap_opts_only)
    result = repositoriesblocklist._calc_internal_blocklist(
        handler, external_tasks, enabled_repoids=set()
    )

    if exp_report_title:
        assert reporting.create_report.report_fields['title'] == exp_report_title
    else:
        assert reporting.create_report.called == 0

    if exp_blocklist_empty:
        assert not result
    else:
        assert result


def test_get_crb_repos_filters_by_architecture(monkeypatch):
    """Only CRB repos matching the current architecture are returned."""
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        arch='x86_64', src_ver='8.10', dst_ver='9.6', dst_distro='rhel'
    ))

    repos = [
        PESIDRepositoryEntry(
            pesid='rhel9-CRB', major_version='9',
            repoid='crb-x86_64', rhui='', arch='x86_64',
            channel='ga', repo_type='rpm', distro='rhel',
        ),
        PESIDRepositoryEntry(
            pesid='rhel9-CRB', major_version='9',
            repoid='crb-aarch64', rhui='', arch='aarch64',
            channel='ga', repo_type='rpm', distro='rhel',
        ),
    ]
    repo_mapping = RepositoriesMapping(mapping=[], repositories=repos)
    handler = RepoMapDataHandler(repo_mapping)

    result = repositoriesblocklist._get_crb_repos(handler, False)

    assert result == {'crb-x86_64'}


def test_no_report_for_non_rhel_distro(monkeypatch):
    """No exclusion report generated for non-RHEL distros, but repos are still excluded."""
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        arch='x86_64', src_ver='8.10', dst_ver='9.6', src_distro='centos', dst_distro='centos'
    ))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    centos_repomap = RepositoriesMapping(
        mapping=[RepoMapEntry(source='rhel8-CRB', target=['rhel9-CRB'])],
        repositories=[
            PESIDRepositoryEntry(
                pesid='rhel8-CRB', major_version='8',
                repoid='codeready-builder-for-centos-8-x86_64-rpms',
                rhui='', arch='x86_64', channel='ga', repo_type='rpm', distro='centos',
            ),
            PESIDRepositoryEntry(
                pesid='rhel9-CRB', major_version='9',
                repoid='codeready-builder-for-centos-9-x86_64-rpms',
                rhui='', arch='x86_64', channel='ga', repo_type='rpm', distro='centos',
            ),
        ]
    )
    handler = RepoMapDataHandler(centos_repomap)
    result = repositoriesblocklist._calc_internal_blocklist(
        handler, _NO_TASKS, enabled_repoids=set()
    )

    assert result
    assert reporting.create_report.called == 0


def _get_produced_blocklisted():
    return [m for m in api.produce.model_instances if isinstance(m, RepositoriesBlocklisted)]


def test_compute_blocklist_merges_internal_and_external(monkeypatch):
    """
    compute_blocklist merges internal blocklist with external
    ExternalRepoSetupTasks.to_block and produces RepositoriesBlocklisted.
    """
    external_tasks = ExternalRepoSetupTasks(
        to_enable={'some-repo'}, to_block={'ext-blocked-1', 'ext-blocked-2'}, custom=set()
    )
    monkeypatch.setattr(
        repositoriesblocklist, '_calc_internal_blocklist', lambda _rm, _et, _er: {'crb-repo-1'}
    )
    monkeypatch.setattr(api, 'produce', produce_mocked())

    full_blocklist = repositoriesblocklist.compute_blocklist(None, external_tasks, set())

    assert full_blocklist == {'crb-repo-1', 'ext-blocked-1', 'ext-blocked-2'}

    blocklisted_msgs = _get_produced_blocklisted()
    assert len(blocklisted_msgs) == 1
    assert set(blocklisted_msgs[0].repoids) == full_blocklist


def test_compute_blocklist_no_messages_when_empty(monkeypatch):
    """No blocklist messages are produced when blocklist is empty."""
    external_tasks = ExternalRepoSetupTasks(to_enable=set(), to_block=set(), custom=set())
    monkeypatch.setattr(
        repositoriesblocklist, '_calc_internal_blocklist', lambda _rm, _et, _er: set()
    )
    monkeypatch.setattr(api, 'produce', produce_mocked())

    full_blocklist = repositoriesblocklist.compute_blocklist(None, external_tasks, set())

    assert full_blocklist == set()
    assert len(_get_produced_blocklisted()) == 0


def test_compute_blocklist_only_internal(monkeypatch):
    """Only internal blocklist when no external tasks are present."""
    external_tasks = ExternalRepoSetupTasks(to_enable=set(), to_block=set(), custom=set())
    monkeypatch.setattr(
        repositoriesblocklist, '_calc_internal_blocklist', lambda _rm, _et, _er: {'crb-repo-1'}
    )
    monkeypatch.setattr(api, 'produce', produce_mocked())

    full_blocklist = repositoriesblocklist.compute_blocklist(None, external_tasks, set())

    assert full_blocklist == {'crb-repo-1'}
    assert len(_get_produced_blocklisted()) == 1


def test_compute_blocklist_aggregated_external_tasks(monkeypatch):
    """Blocklist from pre-aggregated external tasks is merged with internal."""
    external_tasks = ExternalRepoSetupTasks(
        to_enable={'repo-a', 'repo-b'}, to_block={'ext-1', 'ext-2', 'ext-3'}, custom=set()
    )
    monkeypatch.setattr(
        repositoriesblocklist, '_calc_internal_blocklist', lambda _rm, _et, _er: set()
    )
    monkeypatch.setattr(api, 'produce', produce_mocked())

    full_blocklist = repositoriesblocklist.compute_blocklist(None, external_tasks, set())

    assert full_blocklist == {'ext-1', 'ext-2', 'ext-3'}


def test_compute_blocklist_overlapping_internal_and_external(monkeypatch):
    """Overlapping repoids between internal and external blocklists are deduplicated."""
    external_tasks = ExternalRepoSetupTasks(
        to_enable=set(), to_block={'shared-repo', 'ext-only'}, custom=set()
    )
    monkeypatch.setattr(
        repositoriesblocklist, '_calc_internal_blocklist', lambda _rm, _et, _er: {'shared-repo', 'internal-only'}
    )
    monkeypatch.setattr(api, 'produce', produce_mocked())

    full_blocklist = repositoriesblocklist.compute_blocklist(None, external_tasks, set())

    assert full_blocklist == {'shared-repo', 'internal-only', 'ext-only'}

    blocklisted_msgs = _get_produced_blocklisted()
    assert len(blocklisted_msgs) == 1
    assert set(blocklisted_msgs[0].repoids) == full_blocklist
