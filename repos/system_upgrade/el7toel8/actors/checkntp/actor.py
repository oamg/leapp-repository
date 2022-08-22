from leapp.actors import Actor
from leapp.libraries.actor.checkntp import check_ntp
from leapp.models import InstalledRedHatSignedRPM, NtpMigrationDecision, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckNtp(Actor):
    """
    Check if ntp and/or ntpdate configuration needs to be migrated.
    """

    name = 'check_ntp'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report, NtpMigrationDecision)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        installed_packages = set()

        signed_rpms = self.consume(InstalledRedHatSignedRPM)
        for rpm_pkgs in signed_rpms:
            for pkg in rpm_pkgs.items:
                installed_packages.add(pkg.name)

        self.produce(check_ntp(installed_packages))
