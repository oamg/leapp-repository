from leapp.actors import Actor
from leapp.libraries.actor.checkmemcached import check_memcached
from leapp.libraries.common.rpms import has_package
from leapp.models import InstalledRedHatSignedRPM
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


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
        check_memcached(has_package(InstalledRedHatSignedRPM, 'memcached'))
