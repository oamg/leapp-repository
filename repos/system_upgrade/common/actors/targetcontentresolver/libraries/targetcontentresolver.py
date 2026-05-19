from leapp.libraries.actor import pes_events_scanner, repositoriesblocklist, setuptargetrepos
from leapp.libraries.actor.repomap_loader import scan_repositories


def process():
    """
    Orchestrate the four stages of target content resolution.

    1. Load and produce the repository mapping (repomap.json). The produced
       RepositoriesMapping message is also used directly by the subsequent
       stages, avoiding a redundant round-trip through the message bus.
    2. Determine which target repositories should be excluded (blocklisted),
       e.g. CRB repos that are unsupported and not explicitly enabled.
       Merge with any external blocklist requests from RepositoriesSetupTasks
       and produce RepositoriesBlocklisted / RepositoriesBlacklisted messages.
    3. Process PES events to compute RPM transaction tasks (what to install,
       remove, keep) and determine which new repositories are needed. RPM
       tasks are produced for downstream actors; the set of requested target
       repoids is returned for direct use in stage 4.
    4. Build the final list of target repositories by combining PES-requested
       repoids from stage 3, external repoid requests (to_enable from
       RepositoriesSetupTasks, e.g. from satellite_upgrade_facts), enabled
       source repos, installed package repos, and custom/blacklisted repo
       configuration.
    """
    repositories_map_msg = scan_repositories()

    full_blocklist_repoids, external_repoids_requests = (
        repositoriesblocklist.compute_blocklist(repositories_map_msg)
    )

    pes_requested_repoids = pes_events_scanner.scan_pes_events(repositories_map_msg, full_blocklist_repoids)

    setuptargetrepos.setup_target_repos(
        repositories_map_msg,
        pes_requested_repoids=pes_requested_repoids,
        blacklisted_repoids=full_blocklist_repoids,
        external_repoids_requests=external_repoids_requests,
    )
