from leapp.actors import Actor
from leapp.libraries.actor import checkreportflatpak
from leapp.models import RpmToFlatpakFacts
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckReportFlatpak(Actor):
    """
    Report RPM-to-Flatpak migrations that will be performed during upgrade.

    Consumes facts produced by ScanRpmToFlatpak and creates a report entry
    informing the user which packages will be migrated from RPM to Flatpak.
    """

    name = 'check_report_flatpak'
    consumes = (RpmToFlatpakFacts,)
    produces = ()
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkreportflatpak.process()
