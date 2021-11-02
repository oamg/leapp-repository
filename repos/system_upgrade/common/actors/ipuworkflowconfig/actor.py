from leapp.actors import Actor
from leapp.libraries.actor import ipuworkflowconfig
from leapp.models import IPUConfig
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag


class IPUWorkflowConfig(Actor):
    """
    IPU workflow config actor
    """

    name = 'ipu_workflow_config'
    consumes = ()
    produces = (IPUConfig, Report)
    tags = (IPUWorkflowTag,)

    def process(self):
        ipuworkflowconfig.produce_ipu_config(self)
