from collections import namedtuple

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import pes_events_scanner, repositoriesblocklist, setuptargetrepos
from leapp.libraries.actor.repomap_loader import scan_repositories
from leapp.libraries.stdlib import api
from leapp.models import CustomTargetRepository, RepositoriesBlacklisted, RepositoriesFacts, RepositoriesSetupTasks
from leapp.utils.deprecation import suppress_deprecation


class MissingMessage(Exception):
    """
    Raised when specified leapp message is missing.
    """
    def __init__(self, message_type):
        self.message_type = message_type
        super().__init__(f'Missing leapp message {message_type}')


ExternalRepoSetupTasks = namedtuple('ExternalRepoSetupTasks', ('to_enable', 'blocklist', 'custom'))

@suppress_deprecation(RepositoriesBlacklisted)
def _get_external_reposetup_tasks():
    """
    Collect repository related tasks from other actors (or configs in future).

    This includes consumption of RepositoriesSetupTasks and CustomTargetRepository.
    The second one should be understood as task as well based on the definition,
    even when the name does not suggest it's actually task as well.

    Return named tuple with `to_enable`, `blocklist`, and `custom` fields.
    The last one is based on reposids in CustomTargetRepository messages.
    """
    tasks = ExternalRepoSetupTasks(set(), set(), set())
    for task in api.consume(RepositoriesSetupTasks):
        tasks.blocklist.update(task.blocklist)
        tasks.to_enable.update(task.to_enable)

    # DEPRECATED: Drop after 2026-07
    for task in api.consume(RepositoriesBlacklisted):
        tasks.blocklist.update(task.repoids)

    tasks.custom.update({repo.repoid for repo in api.consume(CustomTargetRepository)})
    return tasks


def _get_enabled_repoids():
    """
    Return set of repository IDs enabled on the source system.

    The information is consumed from the RepositoriesFacts message.

    :return: Set of all enabled repository IDs present on the source system.
    :rtype: Set[str]
    :raises MissingMessage: When RepositoriesFacts message is missing.
    """
    repos_facts = next(api.consume(RepositoriesFacts), None)
    if not repos_facts:
        raise MissingMessage(RepositoriesFacts)

    enabled_repoids = set()
    for repos in api.consume(RepositoriesFacts):
        for repo_file in repos.repositories:
            for repo in repo_file.data:
                if repo.enabled:
                    enabled_repoids.add(repo.repoid)
    return enabled_repoids


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
    try:
        enabled_repoids = _get_enabled_repoids()
    except MissingMessage as e:
        # TODO(pstodulk): That's placeholder, I expect to stack info about more
        # missing packages as progressing with the changes.
        raise StopActorExecutionError(str(e))

    external_tasks = _get_external_reposetup_tasks()
    repositories_map_msg = scan_repositories()
    blocklisted_repoids = repositoriesblocklist.compute_blocklist(repositories_map_msg, external_tasks)
    pes_requested_repoids = pes_events_scanner.scan_pes_events(
        repositories_map_msg,
        blocklisted_repoids,
        enabled_repoids
    )

    setuptargetrepos.setup_target_repos(
        repositories_map_msg,
        pes_requested_repoids=pes_requested_repoids,
        blacklisted_repoids=blocklisted_repoids,
        external_repoids_requests=external_tasks.to_enable,
    )
