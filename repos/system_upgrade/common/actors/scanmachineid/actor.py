from leapp.actors import Actor
from leapp.libraries.actor import scanmachineid
from leapp.models import MachineIdInfo
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanMachineId(Actor):
    """
    Scan /etc/machine-id and produce machine ID facts for the source system.
    """

    name = 'scan_machine_id'
    consumes = ()
    produces = (MachineIdInfo,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scanmachineid.process()
