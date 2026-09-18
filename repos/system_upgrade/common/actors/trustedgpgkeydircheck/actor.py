from leapp.actors import Actor
from leapp.libraries.actor import trustedgpgkeydircheck
from leapp.models import MisplacedTrustedGpgKeys
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class TrustedGpgKeyDirCheck(Actor):
    """
    Inhibit the upgrade if misplaced GPG keys are found

    RPM GPG keys have to be placed in the correct location within the trusted
    keys directory. Post-quantum (v6) keys belong to the 'pqc' subdirectory of
    the trusted keys directory, while all other (v4) keys belong to its
    top-level. This split is required because not all the tooling used during
    the upgrade can handle keyfiles containing v6 keys.

    Inhibit the upgrade if any misplaced GPG are found and inform the user on
    how to deal with them.
    """

    name = 'trusted_gpg_key_dir_check'
    consumes = (MisplacedTrustedGpgKeys,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        trustedgpgkeydircheck.process()
