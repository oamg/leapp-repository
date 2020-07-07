from leapp.actors import Actor
from leapp.libraries.actor import userspacegen
from leapp.libraries.common.config import get_env, version
from leapp.models import (
    CustomTargetRepositoryFile,
    Report,
    RepositoriesMap,
    RequiredTargetUserspacePackages,
    RHSMInfo,
    RHUIInfo,
    StorageInfo,
    TargetRepositories,
    TargetUserSpaceInfo,
    TMPTargetRepositoriesFacts,
    UsedTargetRepositories,
    XFSPresence,
)
from leapp.tags import IPUWorkflowTag, TargetTransactionFactsPhaseTag
from leapp.utils.deprecation import suppress_deprecation


@suppress_deprecation(TMPTargetRepositoriesFacts)
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
    consumes = (CustomTargetRepositoryFile, RepositoriesMap, RequiredTargetUserspacePackages,
                StorageInfo, RHSMInfo, TargetRepositories, XFSPresence, RHUIInfo)
    produces = (TargetUserSpaceInfo, UsedTargetRepositories, Report, TMPTargetRepositoriesFacts,)
    tags = (IPUWorkflowTag, TargetTransactionFactsPhaseTag)

    def process(self):
        skip_check = get_env('LEAPP_DEVEL_SKIP_CHECK_OS_RELEASE', False)
        if (skip_check or version.is_supported_version()) and next(self.consume(RepositoriesMap), None):
            userspacegen.perform()
