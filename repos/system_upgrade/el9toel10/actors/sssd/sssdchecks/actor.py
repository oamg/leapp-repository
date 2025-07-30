from leapp.actors import Actor
from leapp.libraries.actor import sssdchecks
from leapp.models import KnownHostsProxyConfig
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class SSSDCheck(Actor):
    """
    Check SSSD configuration for changes in RHEL10 and report them in model.
    """

    name = 'sssd_check'
    consumes = (KnownHostsProxyConfig,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        for cfg in self.consume(KnownHostsProxyConfig):
            sssdchecks.check_config(cfg)
