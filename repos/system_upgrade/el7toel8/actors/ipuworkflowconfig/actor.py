from leapp.actors import Actor
from leapp.libraries.actor.library import get_env_vars
from leapp.models import IPUConfig
from leapp.tags import IPUWorkflowTag


class IPUWorkflowConfig(Actor):
    """
    IPU workflow config actor
    """

    name = 'ipu_workflow_config'
    consumes = ()
    produces = (IPUConfig,)
    tags = (IPUWorkflowTag,)

    def process(self):
        self.produce(IPUConfig(leapp_env_vars=get_env_vars()))
