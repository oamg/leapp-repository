from leapp.actors import Actor
from leapp.models import SSSDConfig
from leapp.libraries.actor import sssdupdate
from leapp.tags import PreparationPhaseTag, IPUWorkflowTag


class SSSDUpdate(Actor):
    """
    Update SSSD's and SSH's configuration to use sss_ssh_knownhosts instead
    of sss_ssh_knownhosts proxy.
    """

    name = 'sssd_update'
    consumes = (SSSDConfig,)
    produces = ()
    tags = (IPUWorkflowTag, PreparationPhaseTag)

    def process(self):
        for cfg in self.consume(SSSDConfig):
            sssdupdate.update_config(cfg)
