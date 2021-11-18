from leapp.actors import Actor
from leapp.models import RpmTransactionTasks
from leapp.tags import IPUWorkflowTag, FactsPhaseTag
from leapp.libraries.actor import transactionworkarounds


class TransactionWorkarounds(Actor):
    """
    Provides additional RPM transaction tasks based on bundled RPM packages.

    After collecting bundled RPM packages, a message with relevant data will be produced.
    """

    name = 'transaction_workarounds'
    consumes = ()
    produces = (RpmTransactionTasks,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        transactionworkarounds.process()
