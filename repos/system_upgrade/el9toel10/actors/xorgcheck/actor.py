from leapp.actors import Actor
from leapp.libraries.actor.xorgcheck import report_installed_packages
from leapp.models import DistributionSignedRPM, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class XorgCheck(Actor):
    """
    Inhibit the upgrade if Xorg server packages are present on the system.

    Xorg server is not available in RHEL 10.
    """
    name = 'xorg_check'
    consumes = (DistributionSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        report_installed_packages()
