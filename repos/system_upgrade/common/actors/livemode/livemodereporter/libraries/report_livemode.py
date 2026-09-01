from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import LiveModeConfig


def report_live_mode_if_enabled():
    livemode = next(api.consume(LiveModeConfig), None)
    if not livemode or not livemode.is_enabled:
        return

    storage_part = (
        'The Live Upgrade Mode requires at least 2 GB of additional space '
        'in the partition that hosts /var/lib/leapp in order to create '
        'the squashfs image.'
    )
    memory_part = (
        'During the "reboot phase", the squashfs image will be pulled over '
        'the network into memory. The recommended memory for this mode is '
        'at least 4 GB.'
    )

    summary = storage_part
    if livemode.url_to_load_squashfs_from:
        summary = '{storage} {memory}'.format(storage=storage_part, memory=memory_part)
    reporting.create_report([
        reporting.Title('Live Upgrade Mode enabled'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.BOOT]),
        reporting.RelatedResource('file', '/etc/leapp/files/devel-livemode.ini')
    ])
