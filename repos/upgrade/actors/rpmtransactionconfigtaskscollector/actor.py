from leapp.actors import Actor
from leapp.models import RpmTransactionTasks
from leapp.tags import FactsPhaseTag, IPUWorkflowTag
from leapp.libraries.actor.scanner import load_tasks

CONFIGURATION_BASE_PATH='/etc/leapp/transaction'

class RpmTransactionConfigTasksCollector(Actor):
    name = 'rpm_transaction_config_tasks_collector'
    description = 'Loads additional Rpm transaction tasks from the {} directory.'.format(CONFIGURATION_BASE_PATH)
    consumes = ()
    produces = (RpmTransactionTasks,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        self.produce(load_tasks(CONFIGURATION_BASE_PATH, self.log))
