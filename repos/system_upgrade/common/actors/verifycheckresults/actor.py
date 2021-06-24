from leapp.actors import Actor
from leapp.reporting import Report
from leapp.libraries.actor.verifycheckresults import check
from leapp.tags import ReportPhaseTag, IPUWorkflowTag


class VerifyCheckResults(Actor):
    """
    Check all generated results messages and notify user about them.

    A report file containing all messages will be generated, together with log messages displayed
    to the user.
    """

    name = 'verify_check_results'
    consumes = (Report,)
    produces = ()
    tags = (ReportPhaseTag, IPUWorkflowTag)

    def process(self):
        check()
