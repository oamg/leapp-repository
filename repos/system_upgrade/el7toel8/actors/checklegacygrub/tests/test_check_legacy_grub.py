import pytest

from leapp.libraries.actor import check_legacy_grub as check_legacy_grub_lib
from leapp.libraries.common import grub as grub_lib
from leapp.libraries.common.testutils import create_report_mocked
from leapp.utils.report import is_inhibitor

VDA_WITH_LEGACY_GRUB = (
    '/dev/vda: x86 boot sector; GRand Unified Bootloader, stage1 version 0x3, '
    'stage2 address 0x2000, stage2 segment 0x200, GRUB version 0.94; partition 1: ID=0x83, '
    'active, starthead 32, startsector 2048, 1024000 sectors; partition 2: ID=0x83, starthead 221, '
    'startsector 1026048, 19945472 sectors, code offset 0x48\n'
)

NVME0N1_VDB_WITH_GRUB = (
    '/dev/nvme0n1: x86 boot sector; partition 1: ID=0x83, active, starthead 32, startsector 2048, 6291456 sectors; '
    'partition 2: ID=0x83, starthead 191, startsector 6293504, 993921024 sectors, code offset 0x63'
)


@pytest.mark.parametrize(
    ('grub_device_to_file_output', 'should_inhibit'),
    [
        ({'/dev/vda': VDA_WITH_LEGACY_GRUB}, True),
        ({'/dev/nvme0n1': NVME0N1_VDB_WITH_GRUB}, False),
        ({'/dev/vda': VDA_WITH_LEGACY_GRUB, '/dev/nvme0n1': NVME0N1_VDB_WITH_GRUB}, True)
    ]
)
def test_check_legacy_grub(monkeypatch, grub_device_to_file_output, should_inhibit):

    def file_cmd_mock(cmd, *args, **kwargs):
        assert cmd[:2] == ['file', '-s']
        return {'stdout': grub_device_to_file_output[cmd[2]]}

    monkeypatch.setattr(check_legacy_grub_lib, 'create_report', create_report_mocked())
    monkeypatch.setattr(grub_lib, 'get_grub_devices', lambda: list(grub_device_to_file_output.keys()))
    monkeypatch.setattr(check_legacy_grub_lib, 'run', file_cmd_mock)

    check_legacy_grub_lib.check_grub_disks_for_legacy_grub()

    assert bool(check_legacy_grub_lib.create_report.called) == should_inhibit
    if should_inhibit:
        assert len(check_legacy_grub_lib.create_report.reports) == 1
        report = check_legacy_grub_lib.create_report.reports[0]
        assert is_inhibitor(report)
