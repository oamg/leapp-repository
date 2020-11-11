from leapp.actors import Actor
from leapp.libraries.actor import cupsmigrate
from leapp.models import CupsChangedFeatures
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class CupsMigrate(Actor):
    """
    cups_migrate actor

    Migrates configuration directives and writes into error log
    if any error was encountered.
    """

    name = 'cups_migrate'
    consumes = (CupsChangedFeatures,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        cupsmigrate.migrate_configuration()
