from leapp.actors import Actor
from leapp.libraries.actor import enablephpmodule
from leapp.models import EnabledModules, RpmTransactionTasks
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class EnablePhpModule(Actor):
    """
    Enable the php:8.2 module on the target system if it was enabled on the source system.

    This actor checks if the php:8.2 module stream was enabled on the source system
    and schedules it for enabling on the target system via RpmTransactionTasks.
    """

    name = 'enable_php_module'
    consumes = (EnabledModules,)
    produces = (RpmTransactionTasks,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        enablephpmodule.enable_php_module()
