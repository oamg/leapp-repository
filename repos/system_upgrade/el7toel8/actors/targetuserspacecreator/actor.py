from leapp.actors import Actor
from leapp.libraries.actor import userspacegen
from leapp.models import (IPUConfig, RequiredTargetUserspacePackages, SourceRHSMInfo, TargetRepositories,
                          TargetRHSMInfo, TargetUserSpaceInfo, UsedTargetRepositories, XFSPresence)
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


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
    consumes = (IPUConfig, RequiredTargetUserspacePackages, SourceRHSMInfo, TargetRepositories, XFSPresence)
    produces = (TargetRHSMInfo, TargetUserSpaceInfo, UsedTargetRepositories)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        userspacegen.perform()
