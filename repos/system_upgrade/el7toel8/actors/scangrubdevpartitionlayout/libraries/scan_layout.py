from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import GRUBDevicePartitionLayout, GrubInfo, PartitionInfo

SAFE_OFFSET_BYTES = 1024*1024  # 1MiB


def split_on_space_segments(line):
    fragments = (fragment.strip() for fragment in line.split(' '))
    return [fragment for fragment in fragments if fragment]


def get_partition_layout(device):
    try:
        partition_table = run(['fdisk', '-l', '-u=sectors', device], split=True)['stdout']
    except CalledProcessError as err:
        # Unlikely - if the disk has no partition table, `fdisk` terminates with 0 (no err). Fdisk exits with an err
        # when the device does not exists, or if it is too small to contain a partition table.

        err_msg = 'Failed to run `fdisk` to obtain the partition table of the device {0}. Full error: \'{1}\''
        api.current_logger().error(err_msg.format(device, str(err)))
        return None

    table_iter = iter(partition_table)

    for line in table_iter:
        if not line.startswith('Units'):
            # We are still reading general device information and not the table itself
            continue

        unit = line.split('=')[2].strip()  # Contains '512 bytes'
        unit = int(unit.split(' ')[0].strip())
        break  # First line of the partition table header

    for line in table_iter:
        line = line.strip()
        if not line.startswith('Device'):
            continue

        part_all_attrs = split_on_space_segments(line)
        break

    partitions = []
    for partition_line in table_iter:
        # Fields:               Device     Boot   Start      End  Sectors Size Id Type
        # The line looks like: `/dev/vda1  *       2048  2099199  2097152   1G 83 Linux`
        part_info = split_on_space_segments(partition_line)

        # If the partition is not bootable, the Boot column might be empty
        part_device = part_info[0]
        part_start = int(part_info[2]) if len(part_info) == len(part_all_attrs) else int(part_info[1])
        partitions.append(PartitionInfo(part_device=part_device, start_offset=part_start*unit))

    return GRUBDevicePartitionLayout(device=device, partitions=partitions)


def scan_grub_device_partition_layout():
    grub_devices = next(api.consume(GrubInfo), None)
    if not grub_devices:
        return

    for device in grub_devices.orig_devices:
        dev_info = get_partition_layout(device)
        if dev_info:
            api.produce(dev_info)
