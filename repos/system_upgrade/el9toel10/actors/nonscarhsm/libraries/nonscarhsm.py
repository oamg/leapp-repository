from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import RHSMInfo
from leapp.reporting import create_report


def process():
    for info in api.consume(RHSMInfo):
        if info.is_registered and not info.sca_detected:
            # TODO summary, remediation hint, external link
            create_report(
                [
                    reporting.Title(
                        "The system is not registered to an SCA organization"
                    ),
                    reporting.Summary(
                        "Leapp detected that the system is registered to an SKU organization."
                        " On RHEL 10, Red Hat Subscription Manager cannot be registered to an"
                        " SKU organization."
                    ),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Groups([reporting.Groups.SANITY]),
                    reporting.Groups([reporting.Groups.INHIBITOR]),
                    reporting.Remediation(
                        hint="Register your system with the subscription-manager tool and attach"
                        " proper SKUs to be able to proceed the upgrade or use the --no-rhsm"
                        " leapp option if you want to provide target repositories by yourself."
                    ),
                    reporting.RelatedResource("package", "subscription-manager"),
                    reporting.ExternalLink(url="", title=""),
                ]
            )
