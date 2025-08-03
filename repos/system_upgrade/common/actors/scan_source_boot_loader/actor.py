from leapp.actors import Actor
from leapp.libraries.actor import scan_source_boot_entry as scan_source_boot_entry_lib
from leapp.models import DefaultSourceBootEntry
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanSourceBootEntry(Actor):
    """
    Scan the default boot entry of the source system.
    """

    name = 'scan_source_boot_entry'
    consumes = ()
    produces = (DefaultSourceBootEntry,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scan_source_boot_entry_lib.scan_default_source_boot_entry()
