from leapp.actors import Actor
from leapp.libraries.actor import library
from leapp.models import Report
from leapp.tags import IPUWorkflowTag, TargetTransactionChecksPhaseTag


class ReportSetTargetRelease(Actor):
    """
    Reports that a release will be set in the subscription-manager after the upgrade.
    """

    name = 'report_set_target_release'
    consumes = ()
    produces = (Report,)
    tags = (IPUWorkflowTag, TargetTransactionChecksPhaseTag)

    def process(self):
        library.process()
