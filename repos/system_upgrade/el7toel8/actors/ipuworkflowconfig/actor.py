import platform

from leapp.actors import Actor
from leapp.libraries.actor import library
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
        self.produce(IPUConfig(
            leapp_env_vars=library.get_env_vars(),
            os_release=library.get_os_release('/etc/os-release'),
            architecture=platform.machine()))
