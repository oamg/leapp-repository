from leapp.actors import Actor
from leapp.libraries.actor import checkreportflatpak
from leapp.models import RpmToFlatpakFacts, RpmTransactionTasks
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckReportFlatpak(Actor):
    """
    Report RPM-to-Flatpak migrations and schedule required packages for installation.

    Consumes facts produced by ScanRpmToFlatpak. When RHSM is in use
    (the default), produces RpmTransactionTasks to install the
    redhat-flatpak-preinstall-* packages and flatpak itself as part of the
    main upgrade transaction, and creates an informational report.

    When RHSM is not in use (e.g. Satellite, RHUI, ISO), creates an
    inhibitor report directing the user to install the affected applications
    as Flatpaks manually after the upgrade.
    """

    name = 'check_report_flatpak'
    consumes = (RpmToFlatpakFacts,)
    produces = (Report, RpmTransactionTasks)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        checkreportflatpak.process()
