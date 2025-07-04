from leapp.actors import Actor
from leapp.models import SSSDConfig
from leapp.libraries.actor import sssdchecks
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class SSSDCheck(Actor):
    """
    Check SSSD configuration for changes in RHEL10 and report them in model.
    """

    name = 'sssd_check'
    consumes = (SSSDConfig,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        for cfg in self.consume(SSSDConfig):
            sssdchecks.check_config(cfg)
