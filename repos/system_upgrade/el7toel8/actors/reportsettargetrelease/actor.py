from leapp.actors import Actor
from leapp.reporting import create_report
from leapp import reporting
from leapp.models import Report, TargetRHSMInfo
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class ReportSetTargetRelease(Actor):
    """
    Reports that a release will be set in the subscription-manager after the upgrade.
    """

    name = 'report_set_target_release'
    consumes = (TargetRHSMInfo,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        info = next(self.consume(TargetRHSMInfo), None)
        if info and info.release:
            create_report([
                reporting.Title(
                    'The subscription-manager release is going to be set to {release}'.format(release=info.release)),
                reporting.Summary(
                    'After the upgrade has completed the release of the subscription-manager will be set to {release}.'
                    ' This will ensure that you will receive and keep the version you choose to upgrade to.'.
                    format(release=info.release)
                ),
                reporting.Severity(reporting.Severity.LOW),
                reporting.Tags([reporting.Tags.UPGRADE_PROCESS]),
                reporting.RelatedResource('package', 'subscription-manager')
            ])
