from leapp.actors import Actor
from leapp.libraries.actor import checksystemarch
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckSystemArch(Actor):
    """
    Check if system is running at a supported architecture. If no, inhibit the upgrade process.

    Base on collected system facts, verify if current architecture is supported, otherwise produces
    a message to inhibit upgrade process
    """

    name = 'check_system_arch'
    consumes = ()
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checksystemarch.check_architecture()
