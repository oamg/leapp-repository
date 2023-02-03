from leapp.actors import Actor
from leapp.libraries.actor import rocecheck
from leapp.models import KernelCmdline, Report, RoceDetected
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class RoceCheck(Actor):
    """
    Check whether RoCE is used on the system and well configured for the upgrade.

    This is valid only for IBM Z systems (s390x). If a used RoCE is detected,
        * system must be RHEL 8.7+ (suggesting 8.8+ due to 8.7 EOL)
        * and system must be booted with: net.naming-scheme=rhel-8.7
    otherwise the network is broken due to changed NICs.
    """

    name = 'roce_check'
    consumes = (KernelCmdline, RoceDetected)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        rocecheck.process()
