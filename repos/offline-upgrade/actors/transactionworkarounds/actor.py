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
        to_install = []
        for name in os.listdir(location):
            if name.endswith('.rpm'):
                to_install.append(os.path.join(location, name))
        if to_install:
            self.produce(RpmTransactionTasks(to_install=to_install))
