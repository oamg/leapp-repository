from leapp.actors import Actor
from leapp.libraries.actor import scanmemory
from leapp.models import MemoryInfo
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanMemory(Actor):
    """Scan Memory of the machine."""

    name = 'scanmemory'
    consumes = ()
    produces = (MemoryInfo,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scanmemory.process()
