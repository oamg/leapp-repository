from leapp.actors import Actor
from leapp.libraries.actor import scancpu
from leapp.models import CPUInfo
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class ScanCPU(Actor):
    """Scan CPUs of the machine."""

    name = 'scancpu'
    consumes = ()
    produces = (CPUInfo,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scancpu.process()
