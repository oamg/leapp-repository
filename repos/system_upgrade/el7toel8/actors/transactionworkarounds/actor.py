import os

from leapp.actors import Actor
from leapp.models import RpmTransactionTasks
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


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
        location = self.get_folder_path('bundled-rpms')
        to_install = []
        for name in os.listdir(location):
            to_install.append(os.path.join(location, name))
        if to_install:
            self.produce(RpmTransactionTasks(to_install=to_install))
