from leapp.actors import Actor
from leapp.libraries.actor.library import check_ntp
from leapp.models import Report, InstalledRedHatSignedRPM, NtpMigrationDecision
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckNtp(Actor):
    name = 'check_ntp'
    description = 'Check if ntp and/or ntpdate configuration needs to be migrated.'
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
