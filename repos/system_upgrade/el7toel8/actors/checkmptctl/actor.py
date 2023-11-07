from leapp.actors import Actor
from leapp.libraries.actor.checkmptctl import check_mptctl
from leapp.models import ActiveKernelModulesFacts
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckMptctl(Actor):
    """
    Check if a process uses the mptctl kernel module that will be removed.
    It could prevent the unloading of this module which does not handle HW.
    """
    name = "check_mptctl"
    consumes = (ActiveKernelModulesFacts,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        check_mptctl()
