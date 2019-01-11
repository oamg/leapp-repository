import os

from leapp.actors import Actor
from leapp.models import RpmTransactionTasks
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class TransactionWorkarounds(Actor):
    name = 'transaction_workarounds'
    description = 'No description has been provided for the transaction_workarounds actor.'
    consumes = ()
    produces = (RpmTransactionTasks,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        location = self.get_folder_path('bundled-rpms')
        local_rpms = []
        for name in os.listdir(location):
            if name.endswith('.rpm'):
                local_rpms.append(os.path.join(location, name))
        if local_rpms:
            self.produce(RpmTransactionTasks(local_rpms=local_rpms))
