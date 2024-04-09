from leapp.actors import Actor
from leapp.libraries.actor import reportleftoverpackages
from leapp.models import LeftoverPackages, RemovedPackages
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, RPMUpgradePhaseTag


class ReportLeftoverPackages(Actor):
    """
    Collect messages about leftover RHEL packages from older major versions and generate a report.

    Depending on execution of previous actors,
    generated report contains information that there are still old RHEL packages
    present on the system, which makes it unsupported or lists packages that have been removed.
    """

    name = 'report_leftover_packages'
    consumes = (LeftoverPackages, RemovedPackages)
    produces = (Report,)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        reportleftoverpackages.process()
