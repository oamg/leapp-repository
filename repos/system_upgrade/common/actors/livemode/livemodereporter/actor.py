from leapp.actors import Actor
from leapp.libraries.actor import report_livemode as report_livemode_lib
from leapp.models import LiveModeConfig
from leapp.reporting import Report
from leapp.tags import ExperimentalTag, FactsPhaseTag, IPUWorkflowTag


class LiveModeReporter(Actor):
    """
    Warn the user about the required space and memory to use the live mode if live mode is enabled.
    """

    name = 'live_mode_reporter'
    consumes = (LiveModeConfig,)
    produces = (Report,)
    tags = (ExperimentalTag, IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        report_livemode_lib.report_live_mode_if_enabled()
