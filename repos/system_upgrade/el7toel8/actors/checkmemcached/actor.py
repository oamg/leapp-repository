from leapp.actors import Actor
from leapp.models import InstalledRedHatSignedRPM
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.libraries.actor.library import check_memcached


class CheckMemcached(Actor):
    """
    Check for incompatible changes in memcached configuration.

    Warn that memcached in RHEL8 no longer listens on the UDP port by default
    and the default service configuration binds memcached to the loopback
    interface.
    """

    name = 'check_memcached'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        installed_packages = set()

        signed_rpms = self.consume(InstalledRedHatSignedRPM)
        for rpm_pkgs in signed_rpms:
            for pkg in rpm_pkgs.items:
                installed_packages.add(pkg.name)

        check_memcached('memcached' in installed_packages)
