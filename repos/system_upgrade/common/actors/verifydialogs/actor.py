from leapp.actors import Actor
from leapp.libraries.actor.verifydialogs import check_dialogs
from leapp.models import DialogModel
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, ReportPhaseTag


class VerifyDialogs(Actor):
    """
    Check all dialogs and notify that user needs to make some choices.

    Report messages containing all dialogs with questions that need to be answered will be produced.
    """

    name = 'verify_check_results'
    consumes = (DialogModel,)
    produces = (Report,)
    tags = (ReportPhaseTag, IPUWorkflowTag)

    def process(self):
        check_dialogs(inhibit_if_no_userchoice=self.skip_dialogs)
