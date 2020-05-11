from leapp.actors import Actor
from leapp.libraries.actor import sanebackendsmigrate
from leapp.models import InstalledRedHatSignedRPM
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class SanebackendsMigrate(Actor):
    """
    Actor for migrating sane-backends configuration files.

    Adds USB quirks for support specific USB scanners if they
    are not added during package manager transaction.
    """

    name = 'sanebackends_migrate'
    consumes = (InstalledRedHatSignedRPM,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        sanebackendsmigrate.update_sane()
