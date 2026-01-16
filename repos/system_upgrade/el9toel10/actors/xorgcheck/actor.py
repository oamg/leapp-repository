from leapp.actors import Actor
from leapp.libraries.actor.xorgcheck import report_installed_packages
from leapp.models import DistributionSignedRPM, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class XorgCheck(Actor):
    """
    Actor checking for presence of Xorg server packages installation.

    Provides user with information related to upgrading systems
    with Xorg server packages installed.
    """
    name = 'xorg_check'
    consumes = (DistributionSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        report_installed_packages()
