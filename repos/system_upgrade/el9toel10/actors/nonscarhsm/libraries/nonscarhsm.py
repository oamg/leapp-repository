from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import RHSMInfo
from leapp.reporting import create_report


def process():
    for info in api.consume(RHSMInfo):
        if info.is_registered and not info.sca_detected:
            create_report(
                [
                    reporting.Title(
                        "The system is not registered to an SCA organization"
                    ),
                    reporting.Summary(
                        "Leapp detected that the system is registered to an account based on"
                        " entitlements, and not on Simple Content Access (SCA). Starting from"
                        " RHEL 10, Red Hat Subscription Manager supports only SCA accounts, and"
                        " does not function with entitlement-based accounts."
                    ),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Groups([reporting.Groups.SANITY]),
                    reporting.Groups([reporting.Groups.INHIBITOR]),
                    reporting.Remediation(
                        hint="The account on which this system is registered to must be set in SCA"
                        " mode. Please note that switching the account mode applies to all the"
                        " systems already registered to it, and to the systems that will be"
                        " registered in the future. Please consult the linked documentation"
                        " for a more detailed explanation."
                    ),
                    reporting.RelatedResource("package", "subscription-manager"),
                    reporting.ExternalLink(
                        url="https://access.redhat.com/articles/transition_of_subscription_services_to_the_hybrid_cloud_console",  # noqa: E501; pylint: disable=line-too-long
                        title="Transition of Red Hat's subscription services to the Red Hat Hybrid"
                        "Cloud Console (console.redhat.com)",
                    ),
                ]
            )
