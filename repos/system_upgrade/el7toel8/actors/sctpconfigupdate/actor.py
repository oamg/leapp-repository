from leapp.actors import Actor
from leapp.libraries.actor import sctpupdate
from leapp.models import SCTPConfig
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class SCTPConfigUpdate(Actor):
    """
    Updates the kernel module blacklist for SCTP.

    If the SCTP module is wanted on RHEL8 the modprobe configuration gets updated to remove SCTP from the black listed
    kernel modules.
    """
    name = 'sctp_config_update'
    description = 'This actor updates SCTP configuration for RHEL8.'
    consumes = (SCTPConfig,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        sctpupdate.perform_update()
