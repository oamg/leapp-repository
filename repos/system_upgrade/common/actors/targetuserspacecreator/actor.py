from leapp.actors import Actor
from leapp.libraries.actor import tus_userspacegen
from leapp.models import (
    CustomTargetRepositoryFile,
    InstalledRPM,
    PkgManagerInfo,
    Report,
    RepositoriesFacts,
    RepositoriesFactsTarget,
    RHSMInfo,
    RHUIInfo,
    StorageInfo,
    TargetOSInstallationImage,
    TargetRepositories,
    TargetUserSpaceInfo,
    TargetUserSpacePreupgradeTasks,
    UsedTargetRepositories
)
from leapp.tags import IPUWorkflowTag, TargetTransactionFactsPhaseTag


class TargetUserspaceCreator(Actor):
    """
    Initialize a directory populated as a minimal environment for running target system binaries.

    The target userspace is set up in a directory so it can be entered as a containerized environment and used to
    perform tasks as if the running system were already the target system. This provides access to the target system
    RPM stack, including DNF, and therefore to RPM features from the target system. The userspace environment is also
    used later to generate an initramfs with dracut using the target system binaries such as the kernel and systemd.

    The work is delegated to :func:`leapp.libraries.actor.tus_userspacegen.perform`.
    """

    name = 'target_userspace_creator'
    consumes = (
        CustomTargetRepositoryFile,
        InstalledRPM,
        RHSMInfo,
        RHUIInfo,
        RepositoriesFacts,
        StorageInfo,
        TargetOSInstallationImage,
        TargetRepositories,
        TargetUserSpacePreupgradeTasks,
        PkgManagerInfo,
    )
    produces = (TargetUserSpaceInfo, UsedTargetRepositories, RepositoriesFactsTarget, Report)
    tags = (IPUWorkflowTag, TargetTransactionFactsPhaseTag)

    def process(self):
        tus_userspacegen.perform()
