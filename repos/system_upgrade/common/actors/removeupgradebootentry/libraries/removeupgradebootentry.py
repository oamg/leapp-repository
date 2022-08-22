from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import BootContent, FirmwareFacts


def remove_boot_entry():
    # we need to make sure /boot is mounted before trying to remove the boot entry

    facts_msg = api.consume(FirmwareFacts)
    facts = next(facts_msg, None)
    if not facts:
        raise StopActorExecutionError('Could not identify system firmware',
                                      details={'details': 'Actor did not receive FirmwareFacts message.'})

    mount_points_per_firmware = {
        'bios': ['/boot'],
        'efi': ['/boot', '/boot/efi']
    }

    for mp in mount_points_per_firmware[facts.firmware]:
        try:
            run(['/bin/mount', mp])
        except CalledProcessError:
            # partitions have been most likely already mounted
            pass
    kernel_filepath = get_upgrade_kernel_filepath()
    run([
        '/usr/sbin/grubby',
        '--remove-kernel={0}'.format(kernel_filepath)
    ])
    if architecture.matches_architecture(architecture.ARCH_S390X):
        # on s390x we need to call zipl explicitly because of issue in grubby,
        # otherwise the new boot entry will not be set as default
        # See https://bugzilla.redhat.com/show_bug.cgi?id=1764306
        run(['/usr/sbin/zipl'])

    # TODO: Move calling `mount -a` to a separate actor as it is not really related to removing the upgrade boot entry.
    #       It's worth to call it after removing the boot entry to avoid boot loop in case mounting fails.
    run([
        '/bin/mount', '-a'
    ])


def get_upgrade_kernel_filepath():
    boot_content_msgs = api.consume(BootContent)
    boot_content = next(boot_content_msgs, None)
    if list(boot_content_msgs):
        api.current_logger().warning('Unexpectedly received more than one BootContent message.')
    if not boot_content:
        raise StopActorExecutionError('Could not remove GRUB boot entry for the upgrade initramfs.',
                                      details={'details': 'Did not receive a message about the leapp-provided'
                                                          ' kernel and initramfs.'})
    return boot_content.kernel_path
