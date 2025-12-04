from leapp.actors import Actor
from leapp.libraries.actor import target_uspace_multipath_configs
from leapp.models import MultipathConfigUpdatesInfo, MultipathInfo, TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class RequestMultipathConfsInTargetUserspace(Actor):
    """
    Aggregates information about multipath configs.

    Produces uniform information consisting of copy instructions about which
    multipath configs (original/updated) should be put into the target
    userspace.
    """

    name = 'request_multipath_conf_in_target_userspace'
    consumes = (MultipathInfo, MultipathConfigUpdatesInfo)
    produces = (TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        target_uspace_multipath_configs.process()
