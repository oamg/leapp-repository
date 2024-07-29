from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import UpgradeEFIBootEntry
from leapp.libraries.common.grub import EFIBootInfo


def get_upgrade_efi_boot_number():
    boot_entry_msgs = api.consume(UpgradeEFIBootEntry)
    boot_entry = next(boot_entry_msgs, None)
    if list(boot_entry_msgs):
        api.current_logger().warning('Unexpectedly received more than one UpgradeEFIBootEntry message.')
    if not boot_entry:
        raise StopActorExecutionError('Could not remove UEFI boot entry for the upgrade initramfs.',
                                      details={'details': 'Did not receive a message about the leapp-provided'
                                                          ' kernel and initramfs.'})
    return boot_entry.boot_number


def remove_upgrade_efi_entry():
    # we need to make sure /boot/efi/ is mounted before trying to remove the boot entry
    mount_points = ['/boot', '/boot/efi']
    for mp in mount_points:
        try:
            run(['/bin/mount', mp])
        except CalledProcessError:
            # partitions have been most likely already mounted
            pass
    boot_number = get_upgrade_efi_boot_number()
    run([
        '/usr/sbin/efibootmgr',
        '--delete-bootnum',
        '--bootnum',
        boot_number
    ])

    efibootinfo = EFIBootInfo()
    # TODO: Check if exists (...should always exists)
    next_bootnum = efibootinfo.boot_order[0]
    run(['/usr/sbin/efibootmgr', '--bootnext', next_bootnum])


    # TODO: Move calling `mount -a` to a separate actor as it is not really related to removing the upgrade boot entry.
    #       It's worth to call it after removing the boot entry to avoid boot loop in case mounting fails.
    run(['/bin/mount', '-a'])
