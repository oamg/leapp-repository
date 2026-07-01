from leapp.actors import Actor
from leapp.libraries.actor import removerockylogossymlinks
from leapp.models import DNFWorkaround
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class RemoveRockyLogosSymlinks(Actor):
    """
    Register a workaround to remove Rocky Linux compatibility symlinks.

    Rocky Linux packages (rocky-logos, rocky-release) create symlinks such as
    /usr/share/redhat-logos and /usr/share/redhat-release pointing to their own
    directories. These conflict with the real RHEL packages during the DNF
    transaction. Register "removerockylogossymlinks" script that removes the
    symlinks prior to the DNF upgrade transaction.
    """

    name = 'remove_rocky_logos_symlinks'
    consumes = ()
    produces = (DNFWorkaround,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        removerockylogossymlinks.process()
