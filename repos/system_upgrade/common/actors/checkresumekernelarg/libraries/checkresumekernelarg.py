from leapp.libraries.stdlib import api
from leapp.models import KernelCmdline, TargetKernelCmdlineArgTasks, UpgradeKernelCmdlineArgTasks


def process():
    """
    Remove resume from the upgrade boot entry and restore it on the target.

    The upgrade initramfs omits the dracut resume module, so the resume device
    cannot be resolved during the upgrade boot. This can cause the system to
    hang waiting for the device. Stripping resume argument from the upgrade kernel
    command line avoids the hang. The value is added back to the target kernel
    entry via TargetKernelCmdlineArgTasks so hibernation continues working
    after the upgrade.
    """
    cmdline = next(api.consume(KernelCmdline), None)
    if not cmdline:
        api.current_logger().debug('No KernelCmdline message received, nothing to do.')
        return

    resume_args = [arg for arg in cmdline.parameters if arg.key == 'resume']
    if not resume_args:
        api.current_logger().debug('No resume argument found on the kernel command line.')
        return

    api.current_logger().info(
        'Requesting removal of resume argument from the upgrade kernel command line: %s',
        ['{}={}'.format(a.key, a.value or '') for a in resume_args]
    )

    api.produce(UpgradeKernelCmdlineArgTasks(to_remove=resume_args))
    # When installing the target kernel RPM, the cmdline is copied from the booted system.
    # As we remove the resume= args, we would accidentally remove them also from the
    # target entry. Therefore, we add them back in here.
    api.produce(TargetKernelCmdlineArgTasks(to_add=resume_args))
