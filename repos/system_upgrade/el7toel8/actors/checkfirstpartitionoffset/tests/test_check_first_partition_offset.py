import pytest

from leapp import reporting
from leapp.libraries.actor import check_first_partition_offset
from leapp.libraries.common import grub
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import FirmwareFacts, GRUBDevicePartitionLayout, PartitionInfo
from leapp.reporting import Report
from leapp.utils.report import is_inhibitor


@pytest.mark.parametrize(
    ('devices', 'should_report'),
    [
        (
            [
                GRUBDevicePartitionLayout(device='/dev/vda',
                                          partitions=[PartitionInfo(part_device='/dev/vda1', start_offset=32256)])
            ],
            True
        ),
        (
            [
                GRUBDevicePartitionLayout(device='/dev/vda',
                                          partitions=[PartitionInfo(part_device='/dev/vda1', start_offset=1024*1025)])
            ],
            False
        ),
        (
            [
                GRUBDevicePartitionLayout(device='/dev/vda',
                                          partitions=[PartitionInfo(part_device='/dev/vda1', start_offset=1024*1024)])
            ],
            False
        )
    ]
)
def test_bad_offset_reported(monkeypatch, devices, should_report):
    def consume_mocked(model_cls):
        if model_cls == FirmwareFacts:
            return [FirmwareFacts(firmware='bios')]
        return devices

    monkeypatch.setattr(api, 'consume', consume_mocked)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    check_first_partition_offset.check_first_partition_offset()

    assert bool(reporting.create_report.called) == should_report
