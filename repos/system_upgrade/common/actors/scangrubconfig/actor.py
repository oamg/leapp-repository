from leapp.actors import Actor
from leapp.libraries.actor import scanner
from leapp.models import GrubConfigError
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanGrubConfig(Actor):
    """
    Scan grub configuration files for errors.
    """

    name = 'scan_grub_config'
    consumes = ()
    produces = (GrubConfigError,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        errors = scanner.scan()
        if errors:
            for error in errors:
                self.produce(error)
