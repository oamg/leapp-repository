from leapp import reporting
from leapp.libraries.stdlib import api


def process():
    """Inhibit the upgrade if the system is booted into UEK."""
    uname_r = api.current_actor().configuration.kernel

    if 'uek' not in uname_r:
        api.current_logger().debug('Not a UEK kernel (%s). Skipping.', uname_r)
        return

    api.current_logger().info('Detected UEK kernel: %s', uname_r)
    reporting.create_report([
        reporting.Title('Unbreakable Enterprise Kernel (UEK) is currently in use'),
        reporting.Summary(
            'The system is currently booted into the Unbreakable Enterprise Kernel (UEK).'
            ' The in-place upgrade and conversion are not supported with UEK.'
            ' The system must be booted into the standard Oracle Linux Kernel'
            ' before the upgrade and conversion can proceed.'
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.BOOT]),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.Remediation(
            hint=(
                'To proceed with the upgrade and conversion, boot into the standard Oracle Linux kernel. '
                'Ensure that the kernel package is installed, set the standard Oracle Linux kernel '
                'as the default boot kernel, reboot the system.'
            )
        ),
    ])
