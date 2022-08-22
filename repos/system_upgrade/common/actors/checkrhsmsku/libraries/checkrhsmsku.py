from leapp import reporting
from leapp.libraries.common import rhsm
from leapp.libraries.stdlib import api
from leapp.models import RHSMInfo
from leapp.reporting import create_report

SCA_TEXT = "Content Access Mode is set to Simple Content Access"


def process():
    if not rhsm.skip_rhsm():
        for info in api.consume(RHSMInfo):
            if not info.attached_skus and not info.sca_detected:
                create_report([
                    reporting.Title('The system is not registered or subscribed.'),
                    reporting.Summary(
                        'The system has to be registered and subscribed to be able to proceed'
                        ' with the upgrade, unless the --no-rhsm option is specified when'
                        ' executing leapp.'
                    ),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Groups([reporting.Groups.SANITY]),
                    reporting.Groups([reporting.Groups.INHIBITOR]),
                    reporting.Remediation(
                        hint='Register your system with the subscription-manager tool and attach'
                             ' proper SKUs to be able to proceed the upgrade or use the --no-rhsm'
                             ' leapp option if you want to provide target repositories by yourself.'),
                    reporting.RelatedResource('package', 'subscription-manager')
                ])
