from leapp.actors import Actor
from leapp.libraries.actor import scanrpmtoflatpak
from leapp.models import DistributionSignedRPM, RHSMInfo, RpmToFlatpakFacts
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanRpmToFlatpak(Actor):
    """
    Scan for RPM packages that will be migrated to Flatpak equivalents after upgrade.

    Detects installed RPM packages (e.g. firefox, thunderbird) that Red Hat ships
    as Flatpaks on RHEL 10, and produces RpmToFlatpakFacts describing the planned
    migration so that later actors can report on it and perform the migration.
    """

    name = 'scan_rpm_to_flatpak'
    consumes = (DistributionSignedRPM, RHSMInfo)
    produces = (RpmToFlatpakFacts,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        scanrpmtoflatpak.process()
