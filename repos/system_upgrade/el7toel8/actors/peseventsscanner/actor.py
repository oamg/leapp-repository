from leapp.actors import Actor
from leapp.libraries.actor.peseventsscanner import pes_events_scanner
from leapp.models import (
    InstalledRedHatSignedRPM,
    PESRpmTransactionTasks,
    RepositoriesMap,
    RepositoriesBlacklisted,
    RepositoriesSetupTasks,
    RpmTransactionTasks,
)
from leapp.reporting import Report
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class PesEventsScanner(Actor):
    """
    Provides data about packages events from Package Evolution Service.

    After collecting data from a provided JSON file containing Package Evolution Service events, a
    message with relevant data will be produced to help DNF Upgrade transaction calculation.
    """

    name = 'pes_events_scanner'
    consumes = (InstalledRedHatSignedRPM, RepositoriesBlacklisted, RepositoriesMap, RpmTransactionTasks)
    produces = (PESRpmTransactionTasks, RepositoriesSetupTasks, Report)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        pes_events_scanner('/etc/leapp/files/pes-events.json')
