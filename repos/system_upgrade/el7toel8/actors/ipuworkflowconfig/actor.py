import platform

from leapp.actors import Actor
from leapp.libraries.actor import library
from leapp.models import IPUConfig, Version
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
        target_version = '8.0'
        os_release = library.get_os_release('/etc/os-release')
        self.produce(IPUConfig(
            leapp_env_vars=library.get_env_vars(),
            os_release=os_release,
            architecture=platform.machine(),
            version=Version(source=os_release.version_id, target=target_version)
        ))
