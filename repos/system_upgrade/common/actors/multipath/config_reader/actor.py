from leapp.actors import Actor
from leapp.libraries.actor import multipathconfread
from leapp.models import (
    DistributionSignedRPM,
    MultipathConfFacts8to9,
    MultipathInfo,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks
)
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class MultipathConfRead(Actor):
    """
    Read multipath configuration files and extract the necessary information

    Related files:
      - /etc/multipath.conf
      - /etc/multipath/ - any files inside the directory
      - /etc/xdrdevices.conf

    Two kinds of messages are generated:
      - MultipathInfo - general information about multipath, version agnostic
      - upgrade-path-specific messages such as MultipathConfFacts8to9 (produced only
        when upgrading from 8 to 9)

    Also, if multipath is detected (MultipathInfo is emitted), messages that cause multipath-related
    files to be copied into the target userspace container and their inclusion into upgrade initramfs
    are emitted.
    """

    name = 'multipath_conf_read'
    consumes = (DistributionSignedRPM,)
    produces = (MultipathInfo, MultipathConfFacts8to9, TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        multipathconfread.scan_and_emit_multipath_info()
