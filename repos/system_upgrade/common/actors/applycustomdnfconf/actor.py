from leapp.actors import Actor
from leapp.libraries.actor import applycustomdnfconf
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class ApplyCustomDNFConf(Actor):
    """
    Move /etc/leapp/files/dnf.conf to /etc/dnf/dnf.conf if it exists

    An actor in FactsPhase copies this file to the target userspace if present.
    In such case we also want to use the file on the target system.
    """
    name = "apply_custom_dnf_conf"
    consumes = ()
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        applycustomdnfconf.process()
