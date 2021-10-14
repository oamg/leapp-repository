from leapp.actors import Actor
from leapp.libraries.actor.checkvdo import check_vdo
from leapp.models import Report, InstalledRedHatSignedRPM
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckVdo(Actor):
    """
    Check if vdo devices need to be migrated to lvm management.
    """

    name = 'check_vdo'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        installed_packages = set()

        signed_rpms = self.consume(InstalledRedHatSignedRPM)
        for rpm_pkgs in signed_rpms:
            for pkg in rpm_pkgs.items:
                installed_packages.add(pkg.name)

        self.produce(check_vdo(installed_packages))
