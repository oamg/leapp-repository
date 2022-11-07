
from leapp.actors import Actor
from leapp.libraries.actor import scanzfcp
from leapp.models import TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanZFCP(Actor):
    """
    In case of s390x architecture, check whether ZFCP is used.

    The current check is based just on existence of the /etc/zfcp.conf file.
    If it exists, produce UpgradeInitramfsTasks msg to ensure the file
    is available inside the target userspace to be able to generate the
    upgrade init ramdisk correctly.
    """

    name = 'scanzfcp'
    consumes = ()
    produces = (TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scanzfcp.process()
