from leapp import reporting
from leapp.actors import Actor
from leapp.models import LiveModeConfigFacts
from leapp.reporting import Report
from leapp.tags import ExperimentalTag, FactsPhaseTag, IPUWorkflowTag


class LiveModeReport(Actor):
    """
    Warn the user about the required space and memory to use the live mode
    """

    name = 'live_mode_report'
    consumes = (LiveModeConfigFacts)
    produces = (Report)
    tags = (ExperimentalTag, IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        livemode = next(self.consume(LiveModeConfigFacts), None)
        if not livemode or not livemode.enabled:
            return

        summary = (
            'The Live Upgrade Mode requires at least 4 GB of additional space '
            'in the partition that hosts /var/lib/leapp in order to create '
            'the squashfs image. During the "reboot phase", the image will '
            'need more space into memory, in particular for booting over the '
            'network. The recommended memory for this mode is at least 4 GB.'
        )
        reporting.create_report([
            reporting.Title('Live Upgrade Mode enabled'),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.BOOT]),
            reporting.RelatedResource('file', '/etc/leapp/files/livemode.json')
        ])
