import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import targetcontentresolver
from leapp.libraries.actor.targetcontentresolver import ExternalRepoSetupTasks, InputData
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    CustomTargetRepository,
    RepositoriesBlacklisted,
    RepositoriesFacts,
    RepositoriesSetupTasks,
    RepositoryData,
    RepositoryFile
)
from leapp.utils.deprecation import suppress_deprecation


def test_process_orchestration(monkeypatch):
    """
    Tests that process() wires data between the four stages correctly:
    scan_repositories -> compute_blocklist -> scan_pes_events -> setup_target_repos.
    """
    call_log = []

    fake_repo_map = object()
    fake_blocklist = frozenset({'blocked-repo'})
    fake_external_tasks = ExternalRepoSetupTasks(
        to_enable=frozenset({'ext-repo'}), to_block=frozenset(), custom=frozenset()
    )
    fake_enabled_repoids = frozenset({'enabled-repo'})
    fake_pes_repoids = frozenset({'pes-repo'})

    class FakeInputData:
        def __init__(self):
            call_log.append('InputData')
            self.external_tasks = fake_external_tasks
            self.enabled_repoids = fake_enabled_repoids

    def mock_scan_repositories():
        call_log.append('scan_repositories')
        return fake_repo_map

    def mock_compute_blocklist(repo_mapping, external_tasks):
        call_log.append('compute_blocklist')
        assert repo_mapping is fake_repo_map
        assert external_tasks is fake_external_tasks
        return fake_blocklist

    def mock_scan_pes_events(repo_mapping, blacklisted_repoids, enabled_repoids):
        call_log.append('scan_pes_events')
        assert repo_mapping is fake_repo_map
        assert blacklisted_repoids is fake_blocklist
        assert enabled_repoids is fake_enabled_repoids
        return fake_pes_repoids

    def mock_setup_target_repos(repo_mapping, pes_requested_repoids=None,
                                blacklisted_repoids=None, external_repoids_requests=None):
        call_log.append('setup_target_repos')
        assert repo_mapping is fake_repo_map
        assert pes_requested_repoids is fake_pes_repoids
        assert blacklisted_repoids is fake_blocklist
        assert external_repoids_requests is fake_external_tasks.to_enable

    monkeypatch.setattr(
        'leapp.libraries.actor.targetcontentresolver.InputData',
        FakeInputData,
    )
    monkeypatch.setattr(
        'leapp.libraries.actor.targetcontentresolver.scan_repositories',
        mock_scan_repositories,
    )
    monkeypatch.setattr(
        'leapp.libraries.actor.targetcontentresolver.repositoriesblocklist.compute_blocklist',
        mock_compute_blocklist,
    )
    monkeypatch.setattr(
        'leapp.libraries.actor.targetcontentresolver.pes_events_scanner.scan_pes_events',
        mock_scan_pes_events,
    )
    monkeypatch.setattr(
        'leapp.libraries.actor.targetcontentresolver.setuptargetrepos.setup_target_repos',
        mock_setup_target_repos,
    )

    targetcontentresolver.process()

    assert call_log == [
        'InputData',
        'scan_repositories',
        'compute_blocklist',
        'scan_pes_events',
        'setup_target_repos',
    ]


def _make_repo_facts(repoids_enabled=None, repoids_disabled=None):
    repos_data = []
    for repoid in (repoids_enabled or []):
        repos_data.append(RepositoryData(repoid=repoid, name=repoid, enabled=True))
    for repoid in (repoids_disabled or []):
        repos_data.append(RepositoryData(repoid=repoid, name=repoid, enabled=False))
    return RepositoriesFacts(
        repositories=[RepositoryFile(file='/etc/yum.repos.d/test.repo', data=repos_data)]
    )


def test_inputdata_collects_enabled_repoids(monkeypatch):
    repo_facts = _make_repo_facts(
        repoids_enabled=['repo-a', 'repo-b'],
        repoids_disabled=['repo-c'],
    )
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[repo_facts]))

    indata = InputData()

    assert indata.enabled_repoids == {'repo-a', 'repo-b'}


def test_inputdata_raises_when_repofacts_missing(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[]))

    with pytest.raises(StopActorExecutionError):
        InputData()


def test_inputdata_aggregates_external_tasks(monkeypatch):
    repo_facts = _make_repo_facts(repoids_enabled=['repo-a'])
    setup_tasks_1 = RepositoriesSetupTasks(to_enable=['en-1'], to_block=['bl-1'])
    setup_tasks_2 = RepositoriesSetupTasks(to_enable=['en-2'], to_block=['bl-2', 'bl-3'])
    custom_1 = CustomTargetRepository(repoid='custom-1')
    custom_2 = CustomTargetRepository(repoid='custom-2')

    monkeypatch.setattr(
        api, 'current_actor',
        CurrentActorMocked(msgs=[repo_facts, setup_tasks_1, setup_tasks_2, custom_1, custom_2])
    )

    indata = InputData()

    assert indata.external_tasks.to_enable == {'en-1', 'en-2'}
    assert indata.external_tasks.to_block == {'bl-1', 'bl-2', 'bl-3'}
    assert indata.external_tasks.custom == {'custom-1', 'custom-2'}


def test_inputdata_empty_external_tasks(monkeypatch):
    repo_facts = _make_repo_facts(repoids_enabled=['repo-a'])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[repo_facts]))

    indata = InputData()

    assert indata.external_tasks.to_enable == set()
    assert indata.external_tasks.to_block == set()
    assert indata.external_tasks.custom == set()


def test_inputdata_warns_on_duplicate_repofacts(monkeypatch):
    repo_facts_1 = _make_repo_facts(repoids_enabled=['repo-a'])
    repo_facts_2 = _make_repo_facts(repoids_enabled=['repo-b'])
    monkeypatch.setattr(
        api, 'current_actor',
        CurrentActorMocked(msgs=[repo_facts_1, repo_facts_2])
    )
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    indata = InputData()

    assert indata.enabled_repoids == {'repo-a'}
    assert any('more than one' in msg for msg in api.current_logger.warnmsg)


@suppress_deprecation(RepositoriesBlacklisted)
def test_inputdata_consumes_deprecated_blacklisted(monkeypatch):
    """RepositoriesBlacklisted repoids are added to external_tasks.to_block."""
    repo_facts = _make_repo_facts(repoids_enabled=['repo-a'])
    blacklisted = RepositoriesBlacklisted(repoids=['bl-1', 'bl-2'])

    monkeypatch.setattr(
        api, 'current_actor',
        CurrentActorMocked(msgs=[repo_facts, blacklisted])
    )

    indata = InputData()

    assert indata.external_tasks.to_block == {'bl-1', 'bl-2'}


@suppress_deprecation(RepositoriesBlacklisted)
def test_inputdata_merges_blacklisted_with_setup_tasks(monkeypatch):
    """RepositoriesBlacklisted repoids are merged with RepositoriesSetupTasks.to_block."""
    repo_facts = _make_repo_facts(repoids_enabled=['repo-a'])
    setup_tasks = RepositoriesSetupTasks(to_enable=['en-1'], to_block=['bl-from-setup'])
    blacklisted = RepositoriesBlacklisted(repoids=['bl-from-deprecated'])

    monkeypatch.setattr(
        api, 'current_actor',
        CurrentActorMocked(msgs=[repo_facts, setup_tasks, blacklisted])
    )

    indata = InputData()

    assert indata.external_tasks.to_block == {'bl-from-setup', 'bl-from-deprecated'}
    assert indata.external_tasks.to_enable == {'en-1'}
