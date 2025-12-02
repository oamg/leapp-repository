from leapp.exceptions import StopActorExecution
from leapp.libraries.stdlib import api, CalledProcessError, run


def blk_dev_from_partition(partition):
    """
    Get the block device containing `partition`.

    In case of the block device itself (e.g. /dev/sda), return just the block
    device. In case of a partition, return its block device:
        /dev/sda  -> /dev/sda
        /dev/sda1 -> /dev/sda

    Raise StopActorExecution when unable to get the block device.
    """

    try:
        result = run(['lsblk', '-spnlo', 'name', partition])
    except CalledProcessError:
        msg = 'Could not get parent device of {} partition'.format(partition)
        api.current_logger().warning(msg)
        raise StopActorExecution(msg)

    # lsblk "-s" option prints dependencies in inverse order, so the parent device will always
    # be the last or the only device.
    # Command result example:
    # 'result', {'signal': 0, 'pid': 3872, 'exit_code': 0, 'stderr': u'', 'stdout': u'/dev/vda1\n/dev/vda\n'}
    return result['stdout'].strip().split()[-1]


def get_partition_number(partition):
    """
    Get the partition number of a particular device.

    This method will use `blkid` to determinate what is the partition number
    related to a particular device.

    :param device: The device to be analyzed.
    :type device: str
    :return: The device partition number.
    :rtype: int
    """

    try:
        result = run(
            ['/usr/sbin/blkid', '-p', '-s', 'PART_ENTRY_NUMBER', partition],
        )
        output = result['stdout'].strip()
    except CalledProcessError:
        raise StopActorExecution('Unable to get information about the {} device'.format(partition))

    if not output:
        raise StopActorExecution('The {} device has no PART_ENTRY_NUMBER'.format(partition))

    partition_number = output.split('PART_ENTRY_NUMBER=')[-1].replace('"', '')

    return int(partition_number)


def get_partition_for_dir(directory):
    """
    Get the partition where `directory` resides.

    This function uses grub2-probe internally.

    :param directory: Path to the directory.
    :type directory: str
    :return: The partition, e.g. /dev/sda1
    :rtype: str
    """

    try:
        result = run(['grub2-probe', '--target=device', directory])
    except CalledProcessError:
        msg = 'Could not get name of underlying {} partition'.format(directory)
        api.current_logger().warning(msg)
        raise StopActorExecution(msg)
    except OSError:
        msg = ('Could not get name of underlying {} partition:'
               ' grub2-probe is missing.'
               ' Possibly called on system that does not use GRUB2?').format(directory)
        api.current_logger().warning(msg)
        raise StopActorExecution(msg)

    partition = result['stdout'].strip()
    api.current_logger().info('{} is on {}'.format(directory, partition))

    return partition
