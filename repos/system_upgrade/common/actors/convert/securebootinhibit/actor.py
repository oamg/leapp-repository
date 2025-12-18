from leapp.actors import Actor
from leapp.libraries.actor import securebootinhibit
from leapp.models import FirmwareFacts
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class SecureBootInhibit(Actor):
    """
    Inhibit the conversion if SecureBoot is enabled.
    """

    name = 'secure_boot_inhibit'
    consumes = (FirmwareFacts,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        securebootinhibit.process()
