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

    # Discover disk label type: dos | gpt
    for line in table_iter:
        line = line.strip()
        if not line.startswith('Disk label type'):
            continue
        disk_type = line.split(':')[1].strip()
        break

    if disk_type == 'gpt':
        api.current_logger().info(
            'Detected GPT partition table. Skipping produce of GRUBDevicePartitionLayout message.'
        )
        # NOTE(pstodulk): The GPT table has a different output format than
        # expected below, example (ignore start/end lines):
        # --------------------------- start ----------------------------------
        # #         Start          End    Size  Type            Name
        # 1         2048         4095      1M  BIOS boot
        # 2         4096      2101247      1G  Microsoft basic
        # 3      2101248     41940991     19G  Linux LVM
        # ---------------------------- end -----------------------------------
        # But mainly, in case of GPT, we have nothing to actually check as
        # we are gathering this data now mainly to get information about the
        # actual size of embedding area (MBR gap). In case of GPT, there is
        # bios boot / prep boot partition, which has always 1 MiB and fulfill
        # our expectations. So skip in this case another processing and generation
        # of the msg. Let's improve it in future if we find a reason for it.
        return None

    for line in table_iter:
        line = line.strip()
        if not line.startswith('Device'):
            continue

        break

    partitions = []
    for partition_line in table_iter:
        if not partition_line.startswith('/'):
            # the output can contain warning msg when a partition is not aligned
            # on physical sector boundary, like:
            # ~~~
            # Partition 4 does not start on physical sector boundary.
            # ~~~
            # We know that in case of MBR the line we expect to parse always
            # starts with canonical path. So let's use this condition.
            # See https://issues.redhat.com/browse/RHEL-50947
            continue
        # Fields:               Device     Boot   Start      End  Sectors Size Id Type
        # The line looks like: `/dev/vda1  *       2048  2099199  2097152   1G 83 Linux`
        part_info = split_on_space_segments(partition_line)

        # If the partition is not bootable, the Boot column might be empty
        part_device = part_info[0]
        part_start = int(part_info[2]) if part_info[1] == '*' else int(part_info[1])
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
