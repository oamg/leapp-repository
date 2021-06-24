from leapp.actors import Actor
from leapp.libraries.actor import targetinitramfsgenerator
from leapp.models import (
    InitrdIncludes,  # deprecated
    InstalledTargetKernelVersion,
    TargetInitramfsTasks,
)
from leapp.tags import IPUWorkflowTag, FinalizationPhaseTag
from leapp.utils.deprecation import suppress_deprecation


@suppress_deprecation(InitrdIncludes)
class TargetInitramfsGenerator(Actor):
    """
    Regenerate the target RHEL major version initrd and include files produced by other actors
    """

    name = 'target_initramfs_generator'
    consumes = (InitrdIncludes, InstalledTargetKernelVersion, TargetInitramfsTasks)
    produces = ()
    tags = (FinalizationPhaseTag, IPUWorkflowTag)

    def process(self):
        targetinitramfsgenerator.process()
