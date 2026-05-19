from leapp.libraries.actor import pes_events_scanner, repositoriesblacklist, setuptargetrepos
from leapp.libraries.actor.repositoriesmapping import scan_repositories


def process():
    """
    Orchestrate the four stages of target content resolution.

    1. Load and produce the repository mapping (repomap.json). The produced
       RepositoriesMapping message is also used directly by the subsequent
       stages, avoiding a redundant round-trip through the message bus.
    2. Determine which target repositories should be excluded (blacklisted),
       e.g. CRB repos that are unsupported and not explicitly enabled.
    3. Process PES events to compute RPM transaction tasks (what to install,
       remove, keep) and determine which new repositories are needed. RPM
       tasks are produced for downstream actors; the repository setup tasks
       are returned for direct use in stage 4.
    4. Build the final list of target repositories by combining the internal
       setup tasks from stage 3 with any external RepositoriesSetupTasks
       (e.g. from satellite_upgrade_facts), enabled source repos, installed
       package repos, and custom/blacklisted repo configuration.
    """
    repositories_map_msg = scan_repositories()

    blacklisted_repoids = repositoriesblacklist.process(repositories_map_msg)

    setup_tasks = pes_events_scanner.process(repositories_map_msg, blacklisted_repoids)

    setuptargetrepos.process(repositories_map_msg, internal_setup_tasks=setup_tasks,
                             blacklisted_repoids=blacklisted_repoids)
