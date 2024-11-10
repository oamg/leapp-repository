from leapp.actors import Actor
from leapp.configs.actor.rpm import Transaction_ToInstall, Transaction_ToKeep, Transaction_ToRemove
from leapp.libraries.actor.rpmtransactionconfigtaskscollector import load_tasks
from leapp.models import DistributionSignedRPM, RpmTransactionTasks
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class RpmTransactionConfigTasksCollector(Actor):
    """
    Provides additional RPM transaction tasks from /etc/leapp/transaction.

    After collecting task data from /etc/leapp/transaction directory, a message with relevant data
    will be produced.
    """
    config_schemas = (Transaction_ToInstall, Transaction_ToKeep, Transaction_ToRemove)
    name = 'rpm_transaction_config_tasks_collector'
    consumes = (DistributionSignedRPM,)
    produces = (RpmTransactionTasks,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        self.produce(load_tasks(self.config, self.log))
