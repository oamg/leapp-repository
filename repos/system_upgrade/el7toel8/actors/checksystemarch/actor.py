import platform

from leapp.actors import Actor
from leapp.models import CheckResult
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckSystemArch(Actor):
    name = 'check_system_arch'
    description = 'Verify if system has a supported arch.'
    consumes = ()
    produces = (CheckResult,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if platform.machine() != 'x86_64':
            self.produce(CheckResult(
                severity='Error',
                result='Fail',
                summary='Unsupported arch',
                details='Upgrade process is only supported on x86_64 systems',
                solutions='There is no current solution for this problem'))
