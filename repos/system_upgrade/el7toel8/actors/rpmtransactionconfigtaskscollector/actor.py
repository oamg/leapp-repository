from leapp.actors import Actor
from leapp.libraries.actor.rpmtransactionconfigtaskscollector import load_tasks
from leapp.models import InstalledRedHatSignedRPM, RpmTransactionTasks
from leapp.tags import FactsPhaseTag, IPUWorkflowTag

CONFIGURATION_BASE_PATH = '/etc/leapp/transaction'


class RpmTransactionConfigTasksCollector(Actor):
    """
    Provides additional RPM transaction tasks from /etc/leapp/transaction.

    After collecting task data from /etc/leapp/transaction directory, a message with relevant data
    will be produced.
    """

    name = 'rpm_transaction_config_tasks_collector'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (RpmTransactionTasks,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        self.produce(load_tasks(CONFIGURATION_BASE_PATH, self.log))
