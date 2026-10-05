from leapp.actors import Actor
from leapp.libraries.actor import applytransactionworkarounds
from leapp.models import DNFWorkaround, TargetUserSpaceInfo
from leapp.tags import IPUWorkflowTag, PreparationPhaseTag


class ApplyTransactionWorkarounds(Actor):
    """
    Executes registered workaround scripts on the system before the upgrade transaction
    """

    name = 'applytransactionworkarounds'
    consumes = (DNFWorkaround, TargetUserSpaceInfo)
    produces = ()
    tags = (IPUWorkflowTag, PreparationPhaseTag)

    def process(self):
        applytransactionworkarounds.process()
