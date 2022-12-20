from leapp.actors import Actor
from leapp.libraries.actor import insightsautoregister
from leapp.models import InstalledRPM
from leapp.reporting import Report
from leapp.tags import FirstBootPhaseTag, IPUWorkflowTag


class InsightsAutoregister(Actor):
    """
    Automatically registers system into Red Hat Insights

    The registration is skipped if NO_INSIGHTS_REGISTER=1 environment variable
    is set, the --no-insights-register command line argument present or the
    system isn't registered with subscription-manager.
    """

    name = 'insights_auto_register'
    consumes = (InstalledRPM,)
    produces = (Report,)
    tags = (FirstBootPhaseTag, IPUWorkflowTag)

    def process(self):
        insightsautoregister.process()
