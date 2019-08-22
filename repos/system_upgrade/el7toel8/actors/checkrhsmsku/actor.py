from leapp.actors import Actor
from leapp.libraries.common import rhsm
from leapp.models import Report, SourceRHSMInfo
from leapp.reporting import create_report
from leapp import reporting
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag


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
                    create_report([
                        reporting.Title('The system is not registered or subscribed.'),
                        reporting.Summary(
                            'The system has to be registered and subscribed to be able to proceed the upgrade.'
                        ),
                        reporting.Severity(reporting.Severity.HIGH),
                        reporting.Tags([reporting.Tags.SANITY]),
                        reporting.Flags([reporting.Flags.INHIBITOR]),
                        reporting.Remediation(
                            hint='Register your system with the subscription-manager tool and attach it to proper SKUs'
                                 ' to be able to proceed the upgrade.'),
                        reporting.RelatedResource('package', 'subscription-manager')
                    ])
