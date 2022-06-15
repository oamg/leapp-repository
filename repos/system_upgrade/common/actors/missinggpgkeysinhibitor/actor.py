from leapp.actors import Actor
from leapp.libraries.actor import missinggpgkey
from leapp.models import (
    DNFWorkaround,
    InstalledRPM,
    TargetUserSpaceInfo,
    TMPTargetRepositoriesFacts,
    UsedTargetRepositories
)
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, TargetTransactionChecksPhaseTag


class MissingGpgKeysInhibitor(Actor):
    """
    Check if all used target repositories have signing gpg keys
    imported in the existing RPM DB or they are planned to be imported

    Right now, we can not check the package signatures yet, but we can do some
    best effort estimation based on the gpgkey option in the repofile
    and content of the existing rpm db.

    Also register the DNFWorkaround to import trusted gpg keys - files provided
    inside the GPG_CERTS_FOLDER directory.

    In case that leapp is executed with --nogpgcheck, all actions are skipped.
    """

    name = 'missing_gpg_keys_inhibitor'
    consumes = (
        InstalledRPM,
        TMPTargetRepositoriesFacts,
        TargetUserSpaceInfo,
        UsedTargetRepositories,
    )
    produces = (DNFWorkaround, Report,)
    tags = (IPUWorkflowTag, TargetTransactionChecksPhaseTag,)

    def process(self):
        missinggpgkey.process()
