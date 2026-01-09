from leapp.actors import Actor
from leapp.libraries.actor.motifcheck import report_installed_packages
from leapp.models import DistributionSignedRPM, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class MotifCheck(Actor):
    """
    Actor checking for presence of Motif installation.

    Provides user with information related to upgrading systems
    with Motif installed.
    """
    name = 'motif_check'
    consumes = (DistributionSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        report_installed_packages()
