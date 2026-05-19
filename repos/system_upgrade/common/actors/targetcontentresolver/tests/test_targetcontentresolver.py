from leapp.libraries.actor import targetcontentresolver


def test_process_orchestration(monkeypatch):
    """
    Tests that process() wires data between the four stages correctly:
    scan_repositories -> compute_blocklist -> scan_pes_events -> setup_target_repos.
    """
    call_log = []

    fake_repo_map = object()
    fake_blocklist = frozenset({'blocked-repo'})
    fake_external_repoids = frozenset({'ext-repo'})
    fake_pes_repoids = frozenset({'pes-repo'})

    def mock_scan_repositories():
        call_log.append('scan_repositories')
        return fake_repo_map

    def mock_compute_blocklist(repo_mapping):
        call_log.append('compute_blocklist')
        assert repo_mapping is fake_repo_map
        return fake_blocklist, fake_external_repoids

    def mock_scan_pes_events(repo_mapping, blacklisted_repoids):
        call_log.append('scan_pes_events')
        assert repo_mapping is fake_repo_map
        assert blacklisted_repoids is fake_blocklist
        return fake_pes_repoids

    def mock_setup_target_repos(repo_mapping, pes_requested_repoids=None,
                                blacklisted_repoids=None, external_repoids_requests=None):
        call_log.append('setup_target_repos')
        assert repo_mapping is fake_repo_map
        assert pes_requested_repoids is fake_pes_repoids
        assert blacklisted_repoids is fake_blocklist
        assert external_repoids_requests is fake_external_repoids

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
        'scan_repositories',
        'compute_blocklist',
        'scan_pes_events',
        'setup_target_repos',
    ]
