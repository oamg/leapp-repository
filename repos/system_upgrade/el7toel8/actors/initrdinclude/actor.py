from leapp.actors import Actor
from leapp.libraries.actor import initrdinclude
from leapp.models import InitrdIncludes, InstalledTargetKernelVersion
from leapp.tags import IPUWorkflowTag, FinalizationPhaseTag


class InitrdInclude(Actor):
    """
    Regenerate RHEL-8 initrd and include files produced by other actors
    """

    name = 'initrdinclude'
    consumes = (InitrdIncludes, InstalledTargetKernelVersion)
    produces = ()
    tags = (FinalizationPhaseTag, IPUWorkflowTag)

    def process(self):
        initrdinclude.process()
