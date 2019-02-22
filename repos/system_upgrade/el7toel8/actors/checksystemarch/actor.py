import platform

from leapp.actors import Actor
from leapp.reporting import Report
from leapp.libraries.common.reporting import report_generic
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckSystemArch(Actor):
    """
    Check if system is running at a supported archtecture. If no, inhibit the upgrade process.

    Base on collected system facts, verify if current archtecture is supported, otherwise produces
    a message to inhibit upgrade process
    """

    name = 'check_system_arch'
    consumes = ()
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if platform.machine() != 'x86_64':
            report_generic(
                title='Unsupported arch',
                summary='Upgrade process is only supported on x86_64 systems.',
                severity='high',
                flags=['inhibitor'])
