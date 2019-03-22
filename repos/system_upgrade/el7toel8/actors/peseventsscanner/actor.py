from leapp.actors import Actor
from leapp.libraries.actor.library import scan_events
from leapp.models import RpmTransactionTasks, RepositoriesSetupTasks, InstalledRedHatSignedRPM
from leapp.reporting import Report
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class PesEventsScanner(Actor):
    """
    Provides data about packages events from Package Evolution Service.

    After collecting data from a provided JSON file containing Package Evolution Service events, a
    message with relevant data will be produced to help DNF Upgrade transaction calculation.
    """

    name = 'pes_events_scanner'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (RpmTransactionTasks, RepositoriesSetupTasks, Report,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scan_events('/etc/leapp/files/pes-events.json')
