from leapp.actors import Actor
from leapp.libraries.actor.sctplib import is_sctp_wanted
from leapp.models import ActiveKernelModulesFacts, SCTPConfig
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class SCTPConfigRead(Actor):
    """
    Determines whether or not the SCTP kernel module might be wanted.

    This actor determines whether or not the SCTP is currently used by this machine or has been quite
    recently used (1 month timeframe). In case it has been used it will issue a SCTPConfig message that
    defines the decision whether or not the SCTP module should be removed from the module blacklist on RHEL8.
    """
    name = 'sctp_read_status'
    consumes = (ActiveKernelModulesFacts,)
    produces = (SCTPConfig,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        self.produce(SCTPConfig(wanted=is_sctp_wanted()))
