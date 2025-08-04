import os

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import DefaultInitramfsInfo


def check_default_initramfs():
    default_initramfs_info = next(api.consume(DefaultInitramfsInfo), None)
    if not default_initramfs_info:
        msg = 'Actor did not receive information about default boot entry\'s initramfs.'
        raise StopActorExecutionError(msg)

    if 'network-legacy' in default_initramfs_info.used_dracut_modules:
        summary = (f'Initramfs ({default_initramfs_info.path}) of the default boot entry uses dracut '
                    'modules that are missing on the target system')
        report_fields = [
            reporting.Title('Use of dracut modules that are missing on the target system detected'),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.BOOT]),
            reporting.Remediation(hint='Remove dracut config file adding the `network-legacy` module'),
            reporting.Groups([reporting.Groups.INHIBITOR]),
        ]

        usual_definition_file = '/etc/dracut.conf.d/50-network-legacy.conf'
        if os.path.exists(usual_definition_file):
            report_fields.append(reporting.RelatedResource('file', usual_definition_file))

        reporting.create_report(report_fields)
