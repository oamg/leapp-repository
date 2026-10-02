from leapp.actors import Actor
from leapp.libraries.actor import tus_userspacegen
from leapp.models import (
    CustomTargetRepositoryFile,
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
    UsedTargetRepositories,
    XFSPresence
)
from leapp.tags import IPUWorkflowTag, TargetTransactionFactsPhaseTag


class TargetUserspaceCreator(Actor):
    """
    Initializes a directory to be populated as a minimal environment to run binaries from the target system.

    The target userspace is set up in a directory so one can run it in a containerized environment to perform tasks
    as if the system running would be the target system. This allows us to use the target system RPM stack including
    DNF which gives us the ability to use RPM features from the target system.
    The userspace environment is also used to generate a initram disk with dracut using the target system binaries
    such as kernel, systemd etc etc
    """

    name = 'target_userspace_creator'
    consumes = (
        CustomTargetRepositoryFile,
        RHSMInfo,
        RHUIInfo,
        RepositoriesFacts,
        StorageInfo,
        TargetOSInstallationImage,
        TargetRepositories,
        TargetUserSpacePreupgradeTasks,
        XFSPresence,
        PkgManagerInfo,
    )
    produces = (TargetUserSpaceInfo, UsedTargetRepositories, RepositoriesFactsTarget, Report)
    tags = (IPUWorkflowTag, TargetTransactionFactsPhaseTag)

    def process(self):
        tus_userspacegen.perform()
