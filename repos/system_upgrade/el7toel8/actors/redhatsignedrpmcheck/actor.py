from leapp.actors import Actor
from leapp.libraries.actor.library import check_unsigned_packages
from leapp.models import InstalledUnsignedRPM
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class RedHatSignedRpmCheck(Actor):
    """
    Check if there are packages not signed by Red Hat in use. If yes, warn user about it.

    If any any installed RPM package does not contain a valid signature from Red Hat, a message
    containing a warning is produced.
    """

    name = 'red_hat_signed_rpm_check'
    consumes = (InstalledUnsignedRPM,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        check_unsigned_packages()
