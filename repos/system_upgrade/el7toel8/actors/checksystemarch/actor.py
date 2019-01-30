import platform

from leapp.actors import Actor
from leapp.models import Inhibitor
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckSystemArch(Actor):
    name = 'check_system_arch'
    description = 'Verify if system has a supported arch.'
    consumes = ()
    produces = (Inhibitor,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if platform.machine() != 'x86_64':
            self.produce(Inhibitor(
                summary='Unsupported arch',
                details='Upgrade process is only supported on x86_64 systems',
                solutions='There is no current solution for this problem'))
