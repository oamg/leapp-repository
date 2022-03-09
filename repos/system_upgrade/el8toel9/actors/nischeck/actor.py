from leapp.actors import Actor
from leapp.libraries.actor.nischeck import report_nis
from leapp.models import InstalledRedHatSignedRPM, NISConfig, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class NISCheck(Actor):
    """
    Checks if any of NIS components is installed and configured
    on the system and warns users about discontinuation.
    """

    name = 'nis_check'
    consumes = (InstalledRedHatSignedRPM, NISConfig)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        report_nis()
