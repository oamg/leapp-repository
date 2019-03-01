from leapp.actors import Actor
from leapp.libraries.actor.library import scan_events
from leapp.models import RpmTransactionTasks, RepositoriesSetupTasks, InstalledRedHatSignedRPM
from leapp.tags import IPUWorkflowTag, FactsPhaseTag, ExperimentalTag


class PesEventsScanner(Actor):
    """
    Provides data about packages events from Package Evolution Service.

    After collecting data from a provided JSON file containing Package Evolution Service events, a
    message with relevant data will be produced to help DNF Upgrade transaction calculation.
    """

    name = 'pes_events_scanner'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (RpmTransactionTasks, RepositoriesSetupTasks,)
    tags = (IPUWorkflowTag, FactsPhaseTag)


    def process(self):
        scan_events(self.get_file_path('pes-events.json'))
