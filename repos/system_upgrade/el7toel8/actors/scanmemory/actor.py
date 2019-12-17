from leapp.actors import Actor
from leapp.libraries.actor import library
from leapp.models import MemoryInfo
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class ScanMemory(Actor):
    """Scan Memory of the machine."""

    name = 'scanmemory'
    consumes = ()
    produces = (MemoryInfo,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        library.process()
