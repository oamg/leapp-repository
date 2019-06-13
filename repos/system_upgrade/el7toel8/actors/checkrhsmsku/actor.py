from leapp.actors import Actor
from leapp.libraries.common import rhsm
from leapp.models import Report, SourceRHSMInfo
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag
from leapp.libraries.common.reporting import report_with_remediation


class CheckRedHatSubscriptionManagerSKU(Actor):
    """
    Ensure the system is subscribed to the subscription manager

    This actor verifies that the system is correctly subscribed to via the Red Hat Subscription Manager and
    has attached SKUs. The actor will inhibit the upgrade if there are none.
    """

    name = 'check_rhsmsku'
    consumes = (SourceRHSMInfo,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        if not rhsm.skip_rhsm():
            for info in self.consume(SourceRHSMInfo):
                if not info.attached_skus:
                    report_with_remediation(
                        title='The system is not registered or subscribed.',
                        summary='The system has to be registered and subscribed to be able to proceed the upgrade.',
                        remediation=(
                            'Register your system with the subscription-manager tool and attach it to proper SKUs'
                            ' to be able to proceed the upgrade.'),
                        severity='high',
                        flags=['inhibitor']
                    )
