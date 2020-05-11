from leapp.actors import Actor
from leapp.libraries.actor import reportsettargetrelease
from leapp.models import Report
from leapp.tags import IPUWorkflowTag, TargetTransactionChecksPhaseTag


class ReportSetTargetRelease(Actor):
    """
    Reports information related to the release set in the subscription-manager after the upgrade.

    When using Red Hat subscription-manager (RHSM), the release is set by default
    to the target version release. In case of skip of the RHSM (--no-rhsm), the
    release stay as it is on the RHEL 7 and user has to handle it manually after
    the upgrade.
    """

    name = 'report_set_target_release'
    consumes = ()
    produces = (Report,)
    tags = (IPUWorkflowTag, TargetTransactionChecksPhaseTag)

    def process(self):
        reportsettargetrelease.process()
