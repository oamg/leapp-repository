from leapp.actors import Actor
from leapp.models import RpmTransactionTasks, SCTPConfig
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class SCTPChecks(Actor):
    """
    Parses collected SCTP information and take necessary actions.

    The only action performed by this actor is to request the installation of the
    kernel-modules-extra rpm package, based on if SCTP is being used or not which
    is collected on SCTPConfig message. If yes, it then produces a RpmTransactionTasks
    requesting to install the package.
    """
    name = 'sctp_checks'
    consumes = (SCTPConfig,)
    produces = (RpmTransactionTasks, )
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        for sctpconfig in self.consume(SCTPConfig):
            if sctpconfig.wanted:
                self.produce(RpmTransactionTasks(to_install=['kernel-modules-extra']))
                break
