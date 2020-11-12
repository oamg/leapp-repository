from leapp.libraries.stdlib import api, run, CalledProcessError, config
from leapp.exceptions import StopActorExecution
from leapp import reporting


def update_grub_core(grub_dev):
    """
    Update GRUB core after upgrade from RHEL7 to RHEL8

    On legacy systems, GRUB core does not get automatically updated when GRUB packages
    are updated.
    """
    cmd = ['grub2-install', grub_dev]
    if config.is_debug():
        cmd += ['-v']
    try:
        run(cmd)
    except CalledProcessError as err:
        reporting.create_report([
            reporting.Title('GRUB core update failed'),
            reporting.Summary(str(err)),
            reporting.Groups([reporting.Groups.BOOT]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Remediation(
                hint='Please run "grub2-install <GRUB_DEVICE>" manually after upgrade'
            )
        ])
        api.current_logger().warning('GRUB core update on {} failed'.format(grub_dev))
        raise StopActorExecution()
    reporting.create_report([
        reporting.Title('GRUB core successfully updated'),
        reporting.Summary('GRUB core on {} was successfully updated'.format(grub_dev)),
        reporting.Groups([reporting.Groups.BOOT]),
        reporting.Severity(reporting.Severity.INFO)
    ])
