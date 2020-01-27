import os

from leapp.actors import Actor
from leapp.models import RootDirectory, RootSubdirectory
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


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
        subdirs = []
        for subdir in os.listdir('/'):
            path = os.path.join('/', subdir)
            if os.path.islink(path):
                subdirs.append(RootSubdirectory(name=subdir, target=os.readlink(path)))
            else:
                subdirs.append(RootSubdirectory(name=subdir))
        self.produce(RootDirectory(items=subdirs))
