from leapp.actors import Actor
from leapp.libraries.actor import trustedgpgkeydircheck
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class TrustedGpgKeyDirCheck(Actor):
    """
    Check the trusted GPG keys directory layout is correct.

    The top-level of the trusted keys directory is expected to contain only v4
    (traditional) keys, while v6 (PQC) keys belong to its 'pqc' subdirectory.
    This split is required because not all the tooling used during the upgrade
    can handle keyfiles containing v6 keys.

    Inhibit the upgrade if any v6 (PQC) key is found at the top-level of the
    directory so the user can move it to the 'pqc' subdirectory.
    """

    name = 'trusted_gpg_key_dir_check'
    consumes = ()
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        trustedgpgkeydircheck.process()
