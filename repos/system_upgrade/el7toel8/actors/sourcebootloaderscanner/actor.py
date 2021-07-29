from leapp.actors import Actor
from leapp.libraries.actor.sourcebootloaderscanner import scan_source_boot_loader_configuration
from leapp.models import SourceBootLoaderConfiguration
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class SourceBootLoaderScanner(Actor):
    """
    Scans the boot loader configuration on the source system.
    """

    name = 'source_boot_loader_scanner'
    consumes = ()
    produces = (SourceBootLoaderConfiguration,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        scan_source_boot_loader_configuration()
