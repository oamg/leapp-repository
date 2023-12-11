from leapp.actors import Actor
from leapp.libraries.actor.baculacheck import report_installed_packages
from leapp.models import DistributionSignedRPM, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class BaculaCheck(Actor):
    """
    Actor checking for presence of Bacula installation.

    Provides user with information related to upgrading systems
    with Bacula installed.
    """
    name = 'bacula_check'
    consumes = (DistributionSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        report_installed_packages()
