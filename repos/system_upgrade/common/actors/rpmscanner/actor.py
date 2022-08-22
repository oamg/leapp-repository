from leapp.actors import Actor
from leapp.libraries.actor import rpmscanner
from leapp.models import InstalledRPM
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class RpmScanner(Actor):
    """
    Provides data about installed RPM Packages.

    After collecting data from RPM query, a message with relevant data will be produced.
    """

    name = 'rpm_scanner'
    consumes = ()
    produces = (InstalledRPM,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        rpmscanner.process()
