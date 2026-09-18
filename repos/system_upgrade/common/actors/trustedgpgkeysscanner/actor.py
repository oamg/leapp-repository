from leapp.actors import Actor
from leapp.libraries.actor import trustedgpgkeys
from leapp.models import InstalledRPM, MisplacedTrustedGpgKeys, TrustedGpgKeys
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class TrustedGpgKeysScanner(Actor):
    """
    Scan for trusted GPG keys.

    These include keys readily available in the source RPM DB, keys for N+1
    Red Hat release and custom keys stored in the trusted directory.

    On 9.9 and 9.10 also search for and produce a MisplacedTrustedGpgKeys
    message with GPG keys misplaced in the trusted directory.
    """

    name = 'trusted_gpg_keys_scanner'
    consumes = (InstalledRPM,)
    produces = (MisplacedTrustedGpgKeys, TrustedGpgKeys)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        trustedgpgkeys.process()
