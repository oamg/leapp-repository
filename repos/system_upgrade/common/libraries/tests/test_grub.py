import os

import pytest

from leapp.exceptions import StopActorExecution
from leapp.libraries.common import grub, mdraid
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import DefaultGrub, DefaultGrubInfo
from leapp.utils.deprecation import suppress_deprecation

EFI_PARTITION = '/dev/vda1'
EFI_DEVICE = '/dev/vda'

BOOT_PARTITION = '/dev/vda2'
BOOT_DEVICE = '/dev/vda'

MD_BOOT_DEVICE = '/dev/md0'
MD_BOOT_DEVICES_WITH_GRUB = ['/dev/sda', '/dev/sdb']

VALID_DD = b'GRUB GeomHard DiskRead Error'
INVALID_DD = b'Nothing to see here!'

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

# pylint: disable=E501
# flake8: noqa: E501
EFIBOOTMGR_OUTPUT = r"""
BootCurrent: 0006
Timeout: 5 seconds
BootOrder: 0003,0004,0001,0006,0000,0002,0007,0005
Boot0000  redhat	VenHw(99e275e7-75a0-4b37-a2e6-c5385e6c00cb)
Boot0001* UEFI: Built-in EFI Shell	VenMedia(5023b95c-db26-429b-a648-bd47664c8012)..BO
Boot0002  Fedora	VenHw(99e275e7-75a0-4b37-a2e6-c5385e6c00cb)
Boot0003* UEFI: PXE IPv4 Intel(R) Network D8:5E:D3:8F:A4:E8	PcieRoot(0x40000)/Pci(0x1,0x0)/Pci(0x0,0x0)/MAC(d85ed38fa4e8,1)/IPv4(0.0.0.00.0.0.0,0,0)..BO
Boot0004* UEFI: PXE IPv4 Intel(R) Network D8:5E:D3:8F:A4:E9	PcieRoot(0x40000)/Pci(0x1,0x0)/Pci(0x0,0x1)/MAC(d85ed38fa4e9,1)/IPv4(0.0.0.00.0.0.0,0,0)..BO
Boot0005  centos	VenHw(99e275e7-75a0-4b37-a2e6-c5385e6c00cb)
Boot0006* Red Hat Enterprise Linux	HD(1,GPT,050609f2-0ad0-43cf-8cdf-e53132b898c9,0x800,0x12c000)/File(\EFI\REDHAT\SHIMAA64.EFI)
Boot0007  CentOS Stream	VenHw(99e275e7-75a0-4b37-a2e6-c5385e6c00cb)
"""
EFIBOOTMGR_OUTPUT_ENTRIES = {
    '0000': grub.EFIBootLoaderEntry(
        '0000',
        'redhat',
        False,
        'VenHw(99e275e7-75a0-4b37-a2e6-c5385e6c00cb)'
    ),
    '0001': grub.EFIBootLoaderEntry(
        '0001',
        'UEFI: Built-in EFI Shell',
        True,
        'VenMedia(5023b95c-db26-429b-a648-bd47664c8012)..BO'
    ),
    '0002': grub.EFIBootLoaderEntry(
        '0002',
        'Fedora',
        False,
        'VenHw(99e275e7-75a0-4b37-a2e6-c5385e6c00cb)'
    ),
    '0003': grub.EFIBootLoaderEntry(
        '0003',
        'UEFI: PXE IPv4 Intel(R) Network D8:5E:D3:8F:A4:E8',
        True,
        'PcieRoot(0x40000)/Pci(0x1,0x0)/Pci(0x0,0x0)/MAC(d85ed38fa4e8,1)/IPv4(0.0.0.00.0.0.0,0,0)..BO'
    ),
    '0004': grub.EFIBootLoaderEntry(
        '0004',
        'UEFI: PXE IPv4 Intel(R) Network D8:5E:D3:8F:A4:E9',
        True,
        'PcieRoot(0x40000)/Pci(0x1,0x0)/Pci(0x0,0x1)/MAC(d85ed38fa4e9,1)/IPv4(0.0.0.00.0.0.0,0,0)..BO'
    ),
    '0005': grub.EFIBootLoaderEntry(
        '0005',
        'centos',
        False,
        'VenHw(99e275e7-75a0-4b37-a2e6-c5385e6c00cb)'
    ),
    '0006': grub.EFIBootLoaderEntry(
        '0006',
        'Red Hat Enterprise Linux',
        True,
        'HD(1,GPT,050609f2-0ad0-43cf-8cdf-e53132b898c9,0x800,0x12c000)/File(\\EFI\\REDHAT\\SHIMAA64.EFI)'
    ),
    '0007': grub.EFIBootLoaderEntry(
        '0007',
        'CentOS Stream',
        False,
        'VenHw(99e275e7-75a0-4b37-a2e6-c5385e6c00cb)'
    ),
}


def raise_call_error(args=None):
    raise CalledProcessError(
        message='A Leapp Command Error occurred.',
        command=args,
        result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': 'fake', 'stderr': 'fake'}
    )


class RunMocked(object):

    def __init__(self, raise_err=False, boot_on_raid=False):
        self.called = 0
        self.args = None
        self.raise_err = raise_err
        self.boot_on_raid = boot_on_raid

    def __call__(self, args, encoding=None, checked=True):
        self.called += 1
        self.args = args
        stdout = ''
        if self.raise_err:
            if checked is True:
                raise_call_error(args)

            return {'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': 'fake', 'stderr': 'fake'}

        if self.args[:-1] == ['grub2-probe', '--target=device']:
            directory = self.args[-1]
            if directory == '/boot':
                stdout = MD_BOOT_DEVICE if self.boot_on_raid else BOOT_PARTITION
            elif directory == '/boot/efi/':
                stdout = EFI_PARTITION
            else:
                raise ValueError('Invalid argument {}'.format(directory))

        elif self.args == ['lsblk', '-spnlo', 'name', BOOT_PARTITION]:
            stdout = BOOT_DEVICE
        elif self.args == ['lsblk', '-spnlo', 'name', EFI_PARTITION]:
            stdout = EFI_DEVICE
        elif self.args[:-1] == ['lsblk', '-spnlo', 'name']:
            stdout = self.args[-1][:-1]
        elif self.args == ['/usr/sbin/efibootmgr', '-v']:
            stdout = EFIBOOTMGR_OUTPUT
        else:
            assert False, 'RunMockedError: Called unexpected cmd not covered by test: {}'.format(self.args)

        return {'stdout': stdout, 'exit_code': 0}


def open_mocked(fn, flags):
    if fn == BOOT_DEVICE or fn in MD_BOOT_DEVICES_WITH_GRUB:
        path = os.path.join(CUR_DIR, 'grub_valid')
    else:
        path = os.path.join(CUR_DIR, 'grub_invalid')
    return open(path, 'r')


def open_invalid(fn, flags):
    return open(os.path.join(CUR_DIR, 'grub_invalid'), 'r')


def read_mocked(f, size):
    return f.read(size)


def close_mocked(f):
    f.close()


@suppress_deprecation(grub.get_grub_device)
def test_get_grub_device_library(monkeypatch):
    run_mocked = RunMocked()
    monkeypatch.setattr(grub, 'run', run_mocked)
    monkeypatch.setattr(os, 'open', open_mocked)
    monkeypatch.setattr(os, 'read', read_mocked)
    monkeypatch.setattr(os, 'close', close_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    result = grub.get_grub_device()
    assert grub.run.called == 2
    assert BOOT_DEVICE == result
    assert not api.current_logger.warnmsg
    assert 'GRUB is installed on {}'.format(result) in api.current_logger.infomsg


@suppress_deprecation(grub.get_grub_device)
def test_get_grub_device_fail_library(monkeypatch):
    # TODO(pstodulk): cover here also case with OSError (covered now in actors,
    # so keeping for the future when we have a time)
    run_mocked = RunMocked(raise_err=True)
    monkeypatch.setattr(grub, 'run', run_mocked)
    monkeypatch.setattr(os, 'open', open_mocked)
    monkeypatch.setattr(os, 'read', read_mocked)
    monkeypatch.setattr(os, 'close', close_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    with pytest.raises(StopActorExecution):
        grub.get_grub_device()
    assert grub.run.called == 1
    err = 'Could not get name of underlying /boot partition'
    assert err in api.current_logger.warnmsg


@suppress_deprecation(grub.get_grub_device)
def test_device_no_grub_library(monkeypatch):
    run_mocked = RunMocked()
    monkeypatch.setattr(grub, 'run', run_mocked)
    monkeypatch.setattr(os, 'open', open_invalid)
    monkeypatch.setattr(os, 'read', read_mocked)
    monkeypatch.setattr(os, 'close', close_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    result = grub.get_grub_device()
    assert grub.run.called == 2
    assert not result


@pytest.mark.parametrize('enabled', [True, False])
def test_is_blscfg_library(monkeypatch, enabled):
    bls_cfg_enabled = DefaultGrubInfo(
        default_grub_info=[DefaultGrub(name='GRUB_ENABLE_BLSCFG', value='true')]
    )

    bls_cfg_not_enabled = DefaultGrubInfo(
        default_grub_info=[DefaultGrub(name='GRUB_ENABLE_BLSCFG', value='false')]
    )

    bls_cfg = bls_cfg_enabled if enabled else bls_cfg_not_enabled

    result = grub.is_blscfg_enabled_in_defaultgrub(bls_cfg)
    if enabled:
        assert result
    else:
        assert not result


def is_mdraid_dev_mocked(dev):
    return dev == '/dev/md0'


def test_get_grub_devices_one_device(monkeypatch):
    run_mocked = RunMocked()
    monkeypatch.setattr(grub, 'run', run_mocked)
    monkeypatch.setattr(os, 'open', open_mocked)
    monkeypatch.setattr(os, 'read', read_mocked)
    monkeypatch.setattr(os, 'close', close_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(mdraid, 'is_mdraid_dev', is_mdraid_dev_mocked)

    result = grub.get_grub_devices()
    assert grub.run.called == 2
    assert [BOOT_DEVICE] == result
    assert not api.current_logger.warnmsg
    assert 'GRUB is installed on {}'.format(",".join(result)) in api.current_logger.infomsg


@pytest.mark.parametrize(
    ',component_devs,expected',
    [
        (['/dev/sda1', '/dev/sdb1'], MD_BOOT_DEVICES_WITH_GRUB),
        (['/dev/sda1', '/dev/sdb1', '/dev/sdc1', '/dev/sdd1'], MD_BOOT_DEVICES_WITH_GRUB),
        (['/dev/sda2', '/dev/sdc1'], ['/dev/sda']),
        (['/dev/sdd3', '/dev/sdb2'], ['/dev/sdb']),
    ]
)
def test_get_grub_devices_raid_device(monkeypatch, component_devs, expected):
    run_mocked = RunMocked(boot_on_raid=True)
    monkeypatch.setattr(grub, 'run', run_mocked)
    monkeypatch.setattr(os, 'open', open_mocked)
    monkeypatch.setattr(os, 'read', read_mocked)
    monkeypatch.setattr(os, 'close', close_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(mdraid, 'is_mdraid_dev', is_mdraid_dev_mocked)

    def get_component_devices_mocked(raid_dev):
        assert raid_dev == MD_BOOT_DEVICE
        return component_devs

    monkeypatch.setattr(mdraid, 'get_component_devices', get_component_devices_mocked)

    result = grub.get_grub_devices()
    assert grub.run.called == 1 + len(component_devs)  # grub2-probe + Nx lsblk
    assert sorted(expected) == result
    assert not api.current_logger.warnmsg
    assert 'GRUB is installed on {}'.format(",".join(result)) in api.current_logger.infomsg


def test_canonical_path_to_efi_format():
    assert grub.canonical_path_to_efi_format('/boot/efi/EFI/redhat/shimx64.efi') == r'\EFI\redhat\shimx64.efi'


def test_EFIBootLoaderEntry__efi_path_to_canonical():
    real = grub.EFIBootLoaderEntry._efi_path_to_canonical(r'\EFI\redhat\shimx64.efi')
    expected = '/boot/efi/EFI/redhat/shimx64.efi'
    assert real == expected


def test_canonical_to_efi_to_canonical():
    canonical = '/boot/efi/EFI/redhat/shimx64.efi'
    efi = grub.canonical_path_to_efi_format(canonical)

    assert grub.EFIBootLoaderEntry._efi_path_to_canonical(efi) == canonical


def test_efi_path_to_canonical_to_efi():
    efi = r'\EFI\redhat\shimx64.efi'
    canonical = grub.EFIBootLoaderEntry._efi_path_to_canonical(efi)

    assert grub.canonical_path_to_efi_format(canonical) == efi


@pytest.mark.parametrize(
    'efi_bin_source, expected',
    [
        ('FvVol(7cb8bdc9-f8eb-4f34-aaea-3ee4af6516a1)/FvFile(462caa21-7614-4503-836e-8ab6f4662331) ', False),
        ('PciRoot(0x0)/Pci(0x2,0x3)/Pci(0x0,0x0)N.....YM....R,Y.', False),
        ('HD(1,GPT,28c77f6b-3cd0-4b22-985f-c99903835d79,0x800,0x12c000)/File(\\EFI\\redhat\\shimx64.efi)', True),
    ]
)
def test_EFIBootLoaderEntry_is_referring_to_file(efi_bin_source, expected):
    bootloader_entry = grub.EFIBootLoaderEntry('0001', 'Redhat', False, efi_bin_source)
    assert bootloader_entry.is_referring_to_file() is expected


@pytest.mark.parametrize(
    'efi_bin_source, expected',
    [
        ('FvVol(7cb8bdc9-f8eb-4f34-aaea-3ee4af6516a1)/FvFile(462caa21-7614-4503-836e-8ab6f4662331) ', None),
        ('PciRoot(0x0)/Pci(0x2,0x3)/Pci(0x0,0x0)N.....YM....R,Y.', None),
        ('HD(1,GPT,28c77f6b-3cd0-4b22-985f-c99903835d79,0x800,0x12c000)/File(\\EFI\\redhat\\shimx64.efi)',
         '/boot/efi/EFI/redhat/shimx64.efi'),
    ]
)
def test_EFIBootLoaderEntry_get_canonical_path(efi_bin_source, expected):
    bootloader_entry = grub.EFIBootLoaderEntry('0001', 'Redhat', False, efi_bin_source)
    assert bootloader_entry.get_canonical_path() == expected


def test_is_efi_success(monkeypatch):
    def exists_mocked(path):
        if path == '/sys/firmware/efi':
            return True
        raise ValueError('Unexpected path checked: {}'.format(path))

    monkeypatch.setattr(os.path, 'exists', exists_mocked)

    assert grub.is_efi() is True


def test_is_efi_fail(monkeypatch):
    def exists_mocked(path):
        if path == '/sys/firmware/efi':
            return False
        raise ValueError('Unexpected path checked: {}'.format(path))

    monkeypatch.setattr(os.path, 'exists', exists_mocked)

    assert grub.is_efi() is False


def test_get_efi_partition_success(monkeypatch):
    monkeypatch.setattr(grub, 'run', RunMocked())
    monkeypatch.setattr(grub, 'is_efi', lambda: True)
    monkeypatch.setattr(os.path, 'exists', lambda path: path == '/boot/efi/')
    monkeypatch.setattr(os.path, 'ismount', lambda path: path == '/boot/efi/')

    assert grub.get_efi_partition() == EFI_PARTITION


def test_get_efi_partition_success_fail_not_efi(monkeypatch):
    monkeypatch.setattr(grub, 'run', RunMocked())
    monkeypatch.setattr(grub, 'is_efi', lambda: False)
    monkeypatch.setattr(os.path, 'exists', lambda path: path == '/boot/efi/')
    monkeypatch.setattr(os.path, 'ismount', lambda path: path == '/boot/efi/')

    with pytest.raises(StopActorExecution) as err:
        grub.get_efi_partition()
        assert 'Unable to get ESP when BIOS is used.' in err


def test_get_efi_partition_success_fail_not_exists(monkeypatch):
    monkeypatch.setattr(grub, 'run', RunMocked())
    monkeypatch.setattr(grub, 'is_efi', lambda: True)
    monkeypatch.setattr(os.path, 'exists', lambda path: False)
    monkeypatch.setattr(os.path, 'ismount', lambda path: path == '/boot/efi/')

    with pytest.raises(StopActorExecution) as err:
        grub.get_efi_partition()
        assert 'The UEFI has been detected but' in err


def test_get_efi_partition_success_fail_not_mounted(monkeypatch):
    monkeypatch.setattr(grub, 'run', RunMocked())
    monkeypatch.setattr(grub, 'is_efi', lambda: True)
    monkeypatch.setattr(os.path, 'exists', lambda path: path == '/boot/efi/')
    monkeypatch.setattr(os.path, 'ismount', lambda path: False)

    with pytest.raises(StopActorExecution) as err:
        grub.get_efi_partition()
        assert 'The UEFI has been detected but' in err


def test_get_efi_device(monkeypatch):
    monkeypatch.setattr(grub, 'run', RunMocked())
    monkeypatch.setattr(grub, 'get_efi_partition', lambda: EFI_PARTITION)

    assert grub.get_efi_device() == EFI_DEVICE


def test_EFIBootInfo_fail_not_efi(monkeypatch):
    monkeypatch.setattr(grub, 'is_efi', lambda: False)

    with pytest.raises(StopActorExecution) as err:
        grub.EFIBootInfo()
        assert 'Unable to collect data about UEFI on a BIOS system.' in err


def test_EFIBootInfo_fail_efibootmgr_error(monkeypatch):
    monkeypatch.setattr(grub, 'is_efi', lambda: True)
    monkeypatch.setattr(grub, 'run', RunMocked(raise_err=True))

    with pytest.raises(StopActorExecution) as err:
        grub.EFIBootInfo()
        assert 'Unable to get information about UEFI boot entries.' in err


def test_EFIBootInfo_success(monkeypatch):
    monkeypatch.setattr(grub, 'is_efi', lambda: True)
    monkeypatch.setattr(grub, 'run', RunMocked())

    efibootinfo = grub.EFIBootInfo()
    assert efibootinfo.current_bootnum == '0006'
    assert efibootinfo.next_bootnum is None
    assert efibootinfo.boot_order == ('0003', '0004', '0001', '0006', '0000', '0002', '0007', '0005')
    assert efibootinfo.entries == EFIBOOTMGR_OUTPUT_ENTRIES
