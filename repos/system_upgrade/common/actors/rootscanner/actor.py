from leapp.actors import Actor
from leapp.libraries.actor.rootscanner import scan_dir
from leapp.models import RootDirectory
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class RootScanner(Actor):
    """
    Scan the system root directory and produce a message containing
    information about its subdirectories.
    """

    name = 'root_scanner'
    consumes = ()
    produces = (RootDirectory,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        self.produce(scan_dir(b'/'))
