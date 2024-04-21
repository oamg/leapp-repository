from leapp import reporting
from leapp.exceptions import StopActorExecution
from leapp.libraries.common import grub as grub_lib
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.reporting import create_report

# There is no grub legacy package on RHEL7, therefore, the system must have been upgraded from RHEL6
MIGRATION_TO_GRUB2_GUIDE_URL = 'https://access.redhat.com/solutions/2643721'


def has_legacy_grub(device):
    try:
        output = run(['file', '-s', device])
    except CalledProcessError as err:
        msg = 'Failed to determine the file type for the special device `{0}`. Full error: `{1}`'
        api.current_logger().warning(msg.format(device, str(err)))

        # According to `file` manpage, the exit code > 0 iff the file does not exists (meaning)
        # that grub_lib.get_grub_devices() is unreliable for some reason (better stop the upgrade),
        # or because the file type could not be determined. However, its manpage directly gives examples
        # of file -s being used on block devices, so this should be unlikely - especially if one would
        # consider that get_grub_devices was able to determine that it is a grub device.
        raise StopActorExecution()

    grub_legacy_version_string = 'GRUB version 0.94'
    return grub_legacy_version_string in output['stdout']


def check_grub_disks_for_legacy_grub():
    # Both GRUB2 and Grub Legacy are recognized by `get_grub_devices`
    grub_devices = grub_lib.get_grub_devices()

    legacy_grub_devices = []
    for device in grub_devices:
        if has_legacy_grub(device):
            legacy_grub_devices.append(device)

    if legacy_grub_devices:
        details = (
            'Leapp detected GRUB Legacy to be installed on the system. '
            'The GRUB Legacy bootloader is unsupported on RHEL7 and GRUB2 must be used instead. '
            'The presence of GRUB Legacy is possible on systems that have been upgraded from RHEL 6 in the past, '
            'but required manual post-upgrade steps have not been performed. '
            'Note that the in-place upgrade from RHEL 6 to RHEL 7 systems is in such a case '
            'considered as unfinished.\n\n'

            'GRUB Legacy has been detected on following devices:\n'
            '{block_devices_fmt}\n'
        )

        hint = (
            'Migrate to the GRUB2 bootloader on the reported devices. '
            'Also finish other post-upgrade steps related to the previous in-place upgrade, the majority of which '
            'is a part of the related preupgrade report for upgrades from RHEL 6 to RHEL 7.'
            'If you are not sure whether all previously required post-upgrade steps '
            'have been performed, consider a clean installation of the RHEL 8 system instead. '
            'Note that the in-place upgrade to RHEL 8 can fail in various ways '
            'if the RHEL 7 system is misconfigured.'
        )

        block_devices_fmt = '\n'.join(legacy_grub_devices)
        create_report([
            reporting.Title("GRUB Legacy is used on the system"),
            reporting.Summary(details.format(block_devices_fmt=block_devices_fmt)),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.BOOT]),
            reporting.Remediation(hint=hint),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.ExternalLink(url=MIGRATION_TO_GRUB2_GUIDE_URL,
                                   title='How to install GRUB2 after a RHEL6 to RHEL7 upgrade'),
        ])
