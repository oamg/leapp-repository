from leapp.actors import Actor
from leapp.models import InstalledRedHatSignedRPM
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.libraries.actor.library import check_chrony


class CheckChrony(Actor):
    """
    Check for incompatible changes in chrony configuration.

    Warn that the default chrony configuration in RHEL8 uses the leapsectz
    directive.
    """

    name = 'check_chrony'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        installed_packages = set()

        signed_rpms = self.consume(InstalledRedHatSignedRPM)
        for rpm_pkgs in signed_rpms:
            for pkg in rpm_pkgs.items:
                installed_packages.add(pkg.name)

        check_chrony('chrony' in installed_packages)
