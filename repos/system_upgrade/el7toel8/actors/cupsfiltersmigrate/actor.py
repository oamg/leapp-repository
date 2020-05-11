from leapp.actors import Actor
from leapp.libraries.actor import cupsfiltersmigrate
from leapp.models import InstalledRedHatSignedRPM
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class CupsfiltersMigrate(Actor):
    """
    Actor for migrating package cups-filters.

    Migrating cups-filters package means adding two directives into
    /etc/cups/cups-browsed.conf - LocalQueueNamingRemoteCUPS and
    CreateIPPPrinterQueues.

    LocalQueueNamingRemoteCUPS directive indicates what will be used as a name
    for local print queue creation - the default is DNS-SD ID of advertised
    print queue now, it was the name of remote print queue in the past.

    CreateIPPPrinterQueues directive serves for telling cups-browsed to create
    local print queues for all available IPP printers.
    """

    name = 'cupsfilters_migrate'
    consumes = (InstalledRedHatSignedRPM,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        cupsfiltersmigrate.update_cups_browsed()
