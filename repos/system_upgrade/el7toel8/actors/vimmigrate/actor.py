from leapp.actors import Actor
from leapp.libraries.actor import vimmigrate
from leapp.models import InstalledRedHatSignedRPM
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class VimMigrate(Actor):
    """
    Modify configuration files of Vim 8.0 and later to keep the same behavior
    as Vim 7.4 and earlier had.
    """

    name = 'vim_migrate'
    consumes = (InstalledRedHatSignedRPM,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        vimmigrate.update_vim()
