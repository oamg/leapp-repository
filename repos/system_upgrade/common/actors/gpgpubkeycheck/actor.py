from leapp.actors import Actor
from leapp.libraries.actor import gpgpubkeycheck
from leapp.models import TrustedGpgKeys
from leapp.reporting import Report
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class GpgPubkeyCheck(Actor):
    """
    Checks no unexpected GPG keys were installed during the upgrade.

    This should be mostly sanity check and this should not happen
    unless something went very wrong, regardless the gpgcheck was
    used (default) or not (with --no-gpgcheck option).
    """

    name = 'gpg_pubkey_check'
    consumes = (TrustedGpgKeys,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ApplicationsPhaseTag,)

    def process(self):
        gpgpubkeycheck.process()
