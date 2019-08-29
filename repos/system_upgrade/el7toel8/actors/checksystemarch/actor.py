import platform

from leapp.actors import Actor
from leapp.reporting import Report, create_report
from leapp import reporting
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
        if platform.machine() != 'aarch64':
            create_report([
                reporting.Title('Unsupported architecture'),
                reporting.Summary('Upgrade process is only supported on aarch64 systems.'),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Tags([reporting.Tags.SANITY]),
                reporting.Flags([reporting.Flags.INHIBITOR])
            ])
