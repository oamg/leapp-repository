from leapp import reporting
from leapp.libraries.stdlib import api, CalledProcessError, config, run


def update_grub_core(grub_devs):
    """
    Update GRUB core after upgrade from RHEL7 to RHEL8

    On legacy systems, GRUB core does not get automatically updated when GRUB packages
    are updated.
    """

    successful = []
    failed = []
    for dev in grub_devs:
        cmd = ['grub2-install', dev]
        if config.is_debug():
            cmd += ['-v']
        try:
            run(cmd)
        except CalledProcessError as err:
            api.current_logger().warning('GRUB core update on {} failed: {}'.format(dev, err))
            failed.append(dev)
            continue

        successful.append(dev)

    if failed:
        if successful:
            # partial failure
            summary = (
                'GRUB was successfully updated on the following devices: {},\n'
                'however GRUB update failed on the following devices: {}'
            ).format(', '.join(successful), ', '.join(failed))
        else:
            summary = 'Leapp failed to update GRUB on {}'.format(', '.join(failed))

        reporting.create_report([
            reporting.Title('GRUB core update failed'),
            reporting.Summary(summary),
            reporting.Groups([reporting.Groups.BOOT]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Remediation(
                hint='Please run "grub2-install <GRUB_DEVICE>" manually after upgrade'
            )
        ])
    else:
        reporting.create_report([
            reporting.Title('GRUB core successfully updated'),
            reporting.Summary('GRUB core on {} was successfully updated'.format(', '.join(successful))),
            reporting.Groups([reporting.Groups.BOOT]),
            reporting.Severity(reporting.Severity.INFO)
        ])
