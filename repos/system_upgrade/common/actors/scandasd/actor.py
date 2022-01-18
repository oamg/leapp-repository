
from leapp.actors import Actor
from leapp.libraries.actor import scandasd
from leapp.models import TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanDASD(Actor):
    """
    In case of s390x architecture, check whether DASD is used.

    The current check is based just on existence of the /etc/dasd.conf file.
    If it exists, produce UpgradeInitramfsTasks msg to ensure the file
    is available inside the target userspace to be able to generate the
    upgrade init ramdisk correctly.
    """

    name = 'scandasd'
    consumes = ()
    produces = (TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scandasd.process()
