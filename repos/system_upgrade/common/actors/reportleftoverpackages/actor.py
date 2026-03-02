from leapp.actors import Actor
from leapp.libraries.actor import reportleftoverpackages
from leapp.models import LeftoverPackages, RemovedPackages
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, RPMUpgradePhaseTag


class ReportLeftoverPackages(Actor):
    """
    Generate a report about leftover distribution packages from older major versions.

    Generated report informs about old distribution packages present on the system,
    which makes it unsupported, and lists packages that have been removed if there
    were any.
    """

    name = 'report_leftover_packages'
    consumes = (LeftoverPackages, RemovedPackages)
    produces = (Report,)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        reportleftoverpackages.process()
