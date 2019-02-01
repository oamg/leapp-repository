import platform

from leapp.actors import Actor
from leapp.models import Inhibitor
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckSystemArch(Actor):
    """
    Check if system is running at a supported archtecture. If no, inhibit the upgrade process.

    Base on collected system facts, verify if current archtecture is supported, otherwise produces
    a message to inhibit upgrade process
    """

    name = 'check_system_arch'
    consumes = ()
    produces = (Inhibitor,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if platform.machine() != 'x86_64':
            self.produce(Inhibitor(
                summary='Unsupported arch',
                details='Upgrade process is only supported on x86_64 systems',
                solutions='There is no current solution for this problem'))
