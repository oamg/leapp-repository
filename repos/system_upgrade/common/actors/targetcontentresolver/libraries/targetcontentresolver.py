from collections import namedtuple

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import pes_events_scanner, repositoriesblocklist, setuptargetrepos
from leapp.libraries.actor.repomap_loader import load_repositories_mapping
from leapp.libraries.stdlib import api
from leapp.models import CustomTargetRepository, RepositoriesBlacklisted, RepositoriesFacts, RepositoriesSetupTasks
from leapp.utils.deprecation import suppress_deprecation

ExternalRepoSetupTasks = namedtuple('ExternalRepoSetupTasks', ('to_enable', 'to_block', 'custom'))


class InputData():
    """
    Provide data from consumed messages
    """

    def __init__(self):
        self._missing_messages = []

        self._get_enabled_repoids()
        self._get_external_reposetup_tasks()

        if self._missing_messages:
            # NOTE(pstodulk): This would be an invalid object,
            # so let's end the story here.
            raise StopActorExecutionError(
                 message='Cannot calculate target content requirements',
                 details={
                     'details': 'Some of required leapp messages are missing.',
                     'missing': [i.__name__ for i in self._missing_messages]
                 }
            )

    def _treat_consume_msg(self, model):
        msgs = api.consume(model)
        msg = next(msgs, None)
        if list(msgs):
            w_msg = f'Unexpectedly received more than one {model.__name__} message.'
            api.current_logger().warning(w_msg)
        if not msg:
            self._missing_messages.append(model)
            return None
        return msg

    @suppress_deprecation(RepositoriesBlacklisted)
    def _get_external_reposetup_tasks(self):
        """
        Collect repository related tasks from other actors (or configs in future).

        This includes consumption of RepositoriesSetupTasks and CustomTargetRepository.
        The second one should be understood as task as well based on the definition,
        even when the name does not suggest it's actually task as well.

        Return named tuple with `to_enable`, `to_block`, and `custom` fields.
        The last one is based on reposids in CustomTargetRepository messages.
        """
        self.external_tasks = ExternalRepoSetupTasks(set(), set(), set())
        for task in api.consume(RepositoriesSetupTasks):
            self.external_tasks.to_block.update(task.to_block)
            self.external_tasks.to_enable.update(task.to_enable)

        # DEPRECATED: Drop after 2026-07
        for task in api.consume(RepositoriesBlacklisted):
            self.external_tasks.to_block.update(task.repoids)

        self.external_tasks.custom.update({repo.repoid for repo in api.consume(CustomTargetRepository)})

    def _get_enabled_repoids(self):
        """
        Return set of repository IDs enabled on the source system.

        The information is consumed from the RepositoriesFacts message.

        :return: Set of all enabled repository IDs present on the source system.
        :rtype: Set[str]
        """
        self.enabled_repoids = set()
        repos_facts = self._treat_consume_msg(RepositoriesFacts)
        if repos_facts is None:
            return

        for repo_file in repos_facts.repositories:
            for repo in repo_file.data:
                if repo.enabled:
                    self.enabled_repoids.add(repo.repoid)


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
    indata = InputData()
    repositories_map_msg = load_repositories_mapping()
    blocklisted_repoids = repositoriesblocklist.compute_blocklist(
        repositories_map_msg,
        indata.external_tasks,
        indata.enabled_repoids
    )
    pes_requested_repoids = pes_events_scanner.scan_pes_events(
        repositories_map_msg,
        blocklisted_repoids,
        indata.enabled_repoids
    )

    setuptargetrepos.setup_target_repos(
        repositories_map_msg,
        pes_requested_repoids=pes_requested_repoids,
        blacklisted_repoids=blocklisted_repoids,
        external_repoids_requests=indata.external_tasks.to_enable,
    )
