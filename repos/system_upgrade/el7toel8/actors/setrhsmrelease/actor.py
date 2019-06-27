from leapp.actors import Actor
from leapp.libraries.actor import setrelease
from leapp.models import TargetRHSMInfo
from leapp.tags import FirstBootPhaseTag, IPUWorkflowTag


class SetRhsmRelease(Actor):
    """
    No documentation has been provided for the set_rhsm_release actor.
    """

    name = 'set_rhsm_release'
    consumes = (TargetRHSMInfo,)
    produces = ()
    tags = (IPUWorkflowTag, FirstBootPhaseTag)

    def process(self):
        setrelease.process()
