import os

from leapp.exceptions import StopActorExecution
from leapp.libraries.common import mdraid
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.utils.deprecation import deprecated


def has_grub(blk_dev):
    """
    Check whether GRUB is present on block device
    """
    try:
        blk = os.open(blk_dev, os.O_RDONLY)
        mbr = os.read(blk, 512)
    except OSError:
        api.current_logger().warning(
            'Could not read first sector of {} in order to identify the bootloader'.format(blk_dev)
        )
        raise StopActorExecution()
    os.close(blk)
    test = 'GRUB'
    if not isinstance(mbr, str):
        test = test.encode('utf-8')

    return test in mbr


def blk_dev_from_partition(partition):
    """
    Find parent device of /boot partition
    """
    try:
        result = run(['lsblk', '-spnlo', 'name', partition])
    except CalledProcessError:
        api.current_logger().warning(
            'Could not get parent device of {} partition'.format(partition)
        )
        raise StopActorExecution()
    # lsblk "-s" option prints dependencies in inverse order, so the parent device will always
    # be the last or the only device.
    # Command result example:
    # 'result', {'signal': 0, 'pid': 3872, 'exit_code': 0, 'stderr': u'', 'stdout': u'/dev/vda1\n/dev/vda\n'}
    return result['stdout'].strip().split()[-1]


def get_boot_partition():
    """
    Get /boot partition name.
    """
    try:
        # call grub2-probe to identify /boot partition
        result = run(['grub2-probe', '--target=device', '/boot'])
    except CalledProcessError:
        api.current_logger().warning(
            'Could not get name of underlying /boot partition'
        )
        raise StopActorExecution()
    except OSError:
        api.current_logger().warning(
            'Could not get name of underlying /boot partition:'
            ' grub2-probe is missing.'
            ' Possibly called on system that does not use GRUB2?'
        )
        raise StopActorExecution()
    boot_partition = result['stdout'].strip()
    api.current_logger().info('/boot is on {}'.format(boot_partition))
    return boot_partition


def get_grub_devices():
    """
    Get block devices where GRUB is located. We assume GRUB is on the same device
    as /boot partition is. In case that device is an md (Multiple Device) device, all
    of the component devices of such a device are considered.

    :return: Devices where GRUB is located
    :rtype: list
    """
    boot_device = get_boot_partition()
    devices = []
    if mdraid.is_mdraid_dev(boot_device):
        component_devs = mdraid.get_component_devices(boot_device)
        blk_devs = [blk_dev_from_partition(dev) for dev in component_devs]
        # remove duplicates as there might be raid on partitions on the same drive
        # even if that's very unusual
        devices = sorted(list(set(blk_devs)))
    else:
        devices.append(blk_dev_from_partition(boot_device))

    have_grub = [dev for dev in devices if has_grub(dev)]
    api.current_logger().info('GRUB is installed on {}'.format(",".join(have_grub)))
    return have_grub


@deprecated(since='2023-06-23', message='This function has been replaced by get_grub_devices')
def get_grub_device():
    """
    Get block device where GRUB is located. We assume GRUB is on the same device
    as /boot partition is.

    """
    boot_partition = get_boot_partition()
    grub_dev = blk_dev_from_partition(boot_partition)
    api.current_logger().info('GRUB is installed on {}'.format(grub_dev))
    # if has_grub(grub_dev):
    return grub_dev if has_grub(grub_dev) else None


def is_blscfg_enabled_in_defaultgrub(default_grub_msg):
    """
    Check if GRUB_ENABLE_BLSCFG is true in /etc/default/grub file
    """
    grub_options_lst = default_grub_msg.default_grub_info
    default_grub_options = {
        option.name: option.value.strip('"') for option in grub_options_lst
    }
    return bool(default_grub_options.get('GRUB_ENABLE_BLSCFG', '') == 'true')
