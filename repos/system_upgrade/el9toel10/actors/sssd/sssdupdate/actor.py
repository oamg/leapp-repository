from leapp.actors import Actor
from leapp.libraries.actor import sssdupdate
from leapp.models import KnownHostsProxyConfig
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class SSSDUpdate(Actor):
    """
    Update SSSD's and SSH's configuration to use sss_ssh_knownhosts instead
    of sss_ssh_knownhosts proxy.
    """

    name = 'sssd_update'
    consumes = (KnownHostsProxyConfig,)
    produces = ()
    tags = (IPUWorkflowTag, ApplicationsPhaseTag)

    def process(self):
        for cfg in self.consume(KnownHostsProxyConfig):
            sssdupdate.update_config(cfg)
