from collections import namedtuple

import pytest

from leapp.libraries.actor import scan_layout as scan_layout_lib
from leapp.libraries.common import grub
from leapp.libraries.common.testutils import create_report_mocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import GRUBDevicePartitionLayout, GrubInfo
from leapp.utils.report import is_inhibitor

Device = namedtuple('Device', ['name', 'partitions', 'sector_size'])
Partition = namedtuple('Partition', ['name', 'start_offset'])


@pytest.mark.parametrize(
    'devices',
    [
        (
            Device(name='/dev/vda', sector_size=512,
                   partitions=[Partition(name='/dev/vda1', start_offset=63),
                               Partition(name='/dev/vda2', start_offset=1000)]),
            Device(name='/dev/vdb', sector_size=1024,
                   partitions=[Partition(name='/dev/vdb1', start_offset=100),
                               Partition(name='/dev/vdb2', start_offset=20000)])
        ),
        (
            Device(name='/dev/vda', sector_size=512,
                   partitions=[Partition(name='/dev/vda1', start_offset=111),
                               Partition(name='/dev/vda2', start_offset=1000)]),
        )
    ]
)
def test_get_partition_layout(monkeypatch, devices):
    device_to_fdisk_output = {}
    for device in devices:
        fdisk_output = [
            'Disk {0}: 42.9 GB, 42949672960 bytes, 83886080 sectors'.format(device.name),
            'Units = sectors of 1 * {sector_size} = {sector_size} bytes'.format(sector_size=device.sector_size),
            'Sector size (logical/physical): 512 bytes / 512 bytes',
            'I/O size (minimum/optimal): 512 bytes / 512 bytes',
            'Disk label type: dos',
            'Disk identifier: 0x0000000da',
            '',
            '   Device Boot      Start         End      Blocks   Id  System',
        ]
        for part in device.partitions:
            part_line = '{0}   *     {1}     2099199     1048576   83  Linux'.format(part.name, part.start_offset)
            fdisk_output.append(part_line)

        device_to_fdisk_output[device.name] = fdisk_output

    def mocked_run(cmd, *args, **kwargs):
        assert cmd[:3] == ['fdisk', '-l', '-u=sectors']
        device = cmd[3]
        output = device_to_fdisk_output[device]
        return {'stdout': output}

    def consume_mocked(*args, **kwargs):
        yield GrubInfo(orig_devices=[device.name for device in devices])

    monkeypatch.setattr(scan_layout_lib, 'run', mocked_run)
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'consume', consume_mocked)

    scan_layout_lib.scan_grub_device_partition_layout()

    assert api.produce.called == len(devices)

    dev_name_to_desc = {dev.name: dev for dev in devices}

    for message in api.produce.model_instances:
        assert isinstance(message, GRUBDevicePartitionLayout)
        dev = dev_name_to_desc[message.device]

        expected_part_name_to_start = {part.name: part.start_offset*dev.sector_size for part in dev.partitions}
        actual_part_name_to_start = {part.part_device: part.start_offset for part in message.partitions}
        assert expected_part_name_to_start == actual_part_name_to_start
