from leapp.actors import Actor
from leapp.libraries.actor import trustedgpgkeydircheck
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class TrustedGpgKeyDirCheck(Actor):
    """
    Check the trusted GPG keys directory layout is correct.

    Post-quantum (v6) keys belong to the 'pqc' subdirectory of the trusted keys
    directory, while all other (non-post-quantum) keys belong to its top-level.
    This split is required because not all the tooling used during the upgrade
    can handle keyfiles containing v6 keys.

    Inhibit the upgrade if any post-quantum (v6) key is found at the top-level of
    the directory or any non-post-quantum key is found in the 'pqc' subdirectory,
    so the user can move the misplaced keys to the correct location.
    """

    name = 'trusted_gpg_key_dir_check'
    consumes = ()
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        trustedgpgkeydircheck.process()
