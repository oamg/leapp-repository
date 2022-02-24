from leapp.actors import Actor
from leapp.libraries.common import dnfplugin
from leapp.models import DNFWorkaround
from leapp.tags import IPUWorkflowTag, PreparationPhaseTag


class ApplyTransactionWorkarounds(Actor):
    """
    Executes registered workaround scripts on the system before the upgrade transaction
    """

    name = 'applytransactionworkarounds'
    consumes = (DNFWorkaround,)
    produces = ()
    tags = (IPUWorkflowTag, PreparationPhaseTag)

    def process(self):
        dnfplugin.apply_workarounds()
