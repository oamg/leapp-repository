from leapp.actors import Actor
from leapp.models import RpmTransactionTasks
from leapp.tags import FactsPhaseTag, IPUWorkflowTag
from leapp.libraries.actor.scanner import load_tasks

CONFIGURATION_BASE_PATH = '/etc/leapp/transaction'


class RpmTransactionConfigTasksCollector(Actor):
    """
    Provides additional RPM transaction tasks from /etc/leapp/transaction.

    After collecting task data from /etc/leapp/transaction directory, a message with relevant data
    will be produced.
    """

    name = 'rpm_transaction_config_tasks_collector'
    consumes = ()
    produces = (RpmTransactionTasks,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        self.produce(load_tasks(CONFIGURATION_BASE_PATH, self.log))
