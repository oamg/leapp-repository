from leapp import reporting
from leapp.libraries.common import utils
from leapp.libraries.common.config import is_conversion
from leapp.libraries.stdlib import api
from leapp.models import KernelInfo


def process():
    """Inhibit the upgrade if the system is booted into UEK."""
    if not is_conversion():
        return

    kernel_info = utils._require_exactly_one_message_of_type(KernelInfo)
    uname_r = kernel_info.uname_r

    if 'uek' not in uname_r:
        api.current_logger().debug('Not a UEK kernel (%s). Skipping.', uname_r)
        return

    api.current_logger().info('Detected UEK kernel: %s', uname_r)
    reporting.create_report([
        reporting.Title('Unbreakable Enterprise Kernel (UEK) is currently in use'),
        reporting.Summary(
            'The system is currently booted into the Unbreakable Enterprise Kernel (UEK).'
            ' The in-place upgrade and conversion are not supported with UEK.'
            ' The system must be booted into the Red Hat Compatible Kernel (RHCK)'
            ' before the upgrade and conversion can proceed.'
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.BOOT]),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.Remediation(
            hint=(
                'To proceed with the upgrade and conversion, boot into the Red Hat Compatible Kernel (RHCK). '
                'Ensure that the kernel package is installed, set the Red Hat Compatible Kernel (RHCK) '
                'as the default boot kernel, reboot the system.'
            )
        ),
    ])
