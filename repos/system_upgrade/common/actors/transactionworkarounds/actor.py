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
        local_rpms = []
        for name in os.listdir(location):
            if name.endswith('.rpm'):
                # It is important to put here the realpath to the files here, because
                # symlinks cannot be resolved properly inside of the target userspace since they use the /installroot
                # mount target
                local_rpms.append(os.path.realpath(os.path.join(location, name)))
        if local_rpms:
            self.produce(RpmTransactionTasks(local_rpms=local_rpms))
