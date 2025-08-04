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
        summary = (
            f'Initramfs ({default_initramfs_info.path}) of the default boot entry uses dracut '
            'modules that are missing on the target system. This could cause a fatal '
            'failure during the upgrade, resulting in unbootable system as '
            'the missing dracut module could prevent creation of the required target '
            'initramfs.\n\n'
            'Namely, the legacy-network dracut module is used on this system, which '
            'could originate from older system installations. The problem is typical '
            'for RHEL 7 and early RHEL 8 systems that were in-place-upgraded to RHEL 9.'
        )
        remediation_hint = (
            'Remove the dracut config file which adds the `network-legacy` dracut module. '
            'Then rebuild existing initramfs images to remove the dracut module from them.'
        )
        report_fields = [
            reporting.Title('Use of dracut modules that are missing on the target system detected'),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.BOOT]),
            reporting.Remediation(hint=remediation_hint),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.ExternalLink(
                url='https://access.redhat.com/solutions/7127576',
                title='leapp upgrade fails to boot after upgrading to RHEL 10.0'
            )
        ]

        usual_definition_file = '/etc/dracut.conf.d/50-network-legacy.conf'
        if os.path.exists(usual_definition_file):
            report_fields.append(reporting.RelatedResource('file', usual_definition_file))

        reporting.create_report(report_fields)
