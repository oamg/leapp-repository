from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import LiveModeConfig


def report_live_mode_if_enabled():
    livemode = next(api.consume(LiveModeConfig), None)
    if not livemode or not livemode.is_enabled:
        return

    summary = (
        'The Live Upgrade Mode requires at least 2 GB of additional space '
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
        reporting.RelatedResource('file', '/etc/leapp/files/devel-livemode.ini')
    ])
