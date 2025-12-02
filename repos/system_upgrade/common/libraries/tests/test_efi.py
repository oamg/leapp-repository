import os
import pytest

from leapp.exceptions import StopActorExecution
from leapp.libraries.common import partitions
from leapp.libraries.common.firmware import efi
from leapp.libraries.stdlib import CalledProcessError

EFI_PARTITION = '/dev/vda1'
EFI_DEVICE = '/dev/vda'

# pylint: disable=line-too-long
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
    '0000': efi.EFIBootLoaderEntry(
        '0000',
        'redhat',
        False,
        'VenHw(99e275e7-75a0-4b37-a2e6-c5385e6c00cb)'
    ),
    '0001': efi.EFIBootLoaderEntry(
        '0001',
        'UEFI: Built-in EFI Shell',
        True,
        'VenMedia(5023b95c-db26-429b-a648-bd47664c8012)..BO'
    ),
    '0002': efi.EFIBootLoaderEntry(
        '0002',
        'Fedora',
        False,
        'VenHw(99e275e7-75a0-4b37-a2e6-c5385e6c00cb)'
    ),
    '0003': efi.EFIBootLoaderEntry(
        '0003',
        'UEFI: PXE IPv4 Intel(R) Network D8:5E:D3:8F:A4:E8',
        True,
        'PcieRoot(0x40000)/Pci(0x1,0x0)/Pci(0x0,0x0)/MAC(d85ed38fa4e8,1)/IPv4(0.0.0.00.0.0.0,0,0)..BO'
    ),
    '0004': efi.EFIBootLoaderEntry(
        '0004',
        'UEFI: PXE IPv4 Intel(R) Network D8:5E:D3:8F:A4:E9',
        True,
        'PcieRoot(0x40000)/Pci(0x1,0x0)/Pci(0x0,0x1)/MAC(d85ed38fa4e9,1)/IPv4(0.0.0.00.0.0.0,0,0)..BO'
    ),
    '0005': efi.EFIBootLoaderEntry(
        '0005',
        'centos',
        False,
        'VenHw(99e275e7-75a0-4b37-a2e6-c5385e6c00cb)'
    ),
    '0006': efi.EFIBootLoaderEntry(
        '0006',
        'Red Hat Enterprise Linux',
        True,
        'HD(1,GPT,050609f2-0ad0-43cf-8cdf-e53132b898c9,0x800,0x12c000)/File(\\EFI\\REDHAT\\SHIMAA64.EFI)'
    ),
    '0007': efi.EFIBootLoaderEntry(
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


class RunMocked:

    def __init__(self, raise_err=False):
        self.called = 0
        self.args = None
        self.raise_err = raise_err

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
            if directory == '/boot/efi/':
                stdout = EFI_PARTITION
            else:
                raise ValueError('Invalid argument {}'.format(directory))

        elif self.args == ['lsblk', '-spnlo', 'name', EFI_PARTITION]:
            stdout = EFI_DEVICE
        elif self.args[:-1] == ['lsblk', '-spnlo', 'name']:
            stdout = self.args[-1][:-1]
        elif self.args == ['/usr/sbin/efibootmgr', '-v']:
            stdout = EFIBOOTMGR_OUTPUT
        else:
            assert False, 'RunMockedError: Called unexpected cmd not covered by test: {}'.format(self.args)

        return {'stdout': stdout, 'exit_code': 0}


def test_canonical_path_to_efi_format():
    assert efi.canonical_path_to_efi_format('/boot/efi/EFI/redhat/shimx64.efi') == r'\EFI\redhat\shimx64.efi'


def test_EFIBootLoaderEntry__efi_path_to_canonical():
    real = efi.EFIBootLoaderEntry._efi_path_to_canonical(r'\EFI\redhat\shimx64.efi')
    expected = '/boot/efi/EFI/redhat/shimx64.efi'
    assert real == expected


def test_canonical_to_efi_to_canonical():
    canonical = '/boot/efi/EFI/redhat/shimx64.efi'
    efi_path = efi.canonical_path_to_efi_format(canonical)

    assert efi.EFIBootLoaderEntry._efi_path_to_canonical(efi_path) == canonical


def test_efi_path_to_canonical_to_efi():
    efi_path = r'\EFI\redhat\shimx64.efi'
    canonical = efi.EFIBootLoaderEntry._efi_path_to_canonical(efi_path)

    assert efi.canonical_path_to_efi_format(canonical) == efi_path


@pytest.mark.parametrize(
    'efi_bin_source, expected',
    [
        ('FvVol(7cb8bdc9-f8eb-4f34-aaea-3ee4af6516a1)/FvFile(462caa21-7614-4503-836e-8ab6f4662331) ', False),
        ('PciRoot(0x0)/Pci(0x2,0x3)/Pci(0x0,0x0)N.....YM....R,Y.', False),
        ('HD(1,GPT,28c77f6b-3cd0-4b22-985f-c99903835d79,0x800,0x12c000)/File(\\EFI\\redhat\\shimx64.efi)', True),
    ]
)
def test_EFIBootLoaderEntry_is_referring_to_file(efi_bin_source, expected):
    bootloader_entry = efi.EFIBootLoaderEntry('0001', 'Redhat', False, efi_bin_source)
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
    bootloader_entry = efi.EFIBootLoaderEntry('0001', 'Redhat', False, efi_bin_source)
    assert bootloader_entry.get_canonical_path() == expected


def test_get_efi_partition_success(monkeypatch):
    monkeypatch.setattr(partitions, 'run', RunMocked())
    monkeypatch.setattr(efi, 'is_efi', lambda: True)
    monkeypatch.setattr(os.path, 'exists', lambda path: path == '/boot/efi/')
    monkeypatch.setattr(os.path, 'ismount', lambda path: path == '/boot/efi/')

    assert efi.get_efi_partition() == EFI_PARTITION


def test_get_efi_partition_success_fail_not_efi(monkeypatch):
    monkeypatch.setattr(partitions, 'run', RunMocked())
    monkeypatch.setattr(efi, 'is_efi', lambda: False)
    monkeypatch.setattr(os.path, 'exists', lambda path: path == '/boot/efi/')
    monkeypatch.setattr(os.path, 'ismount', lambda path: path == '/boot/efi/')

    with pytest.raises(StopActorExecution) as err:
        efi.get_efi_partition()
        assert 'Unable to get ESP when BIOS is used.' in err


def test_get_efi_partition_success_fail_not_exists(monkeypatch):
    monkeypatch.setattr(partitions, 'run', RunMocked())
    monkeypatch.setattr(efi, 'is_efi', lambda: True)
    monkeypatch.setattr(os.path, 'exists', lambda path: False)
    monkeypatch.setattr(os.path, 'ismount', lambda path: path == '/boot/efi/')

    with pytest.raises(StopActorExecution) as err:
        efi.get_efi_partition()
        assert 'The UEFI has been detected but' in err


def test_get_efi_partition_success_fail_not_mounted(monkeypatch):
    monkeypatch.setattr(partitions, 'run', RunMocked())
    monkeypatch.setattr(efi, 'is_efi', lambda: True)
    monkeypatch.setattr(os.path, 'exists', lambda path: path == '/boot/efi/')
    monkeypatch.setattr(os.path, 'ismount', lambda path: False)

    with pytest.raises(StopActorExecution) as err:
        efi.get_efi_partition()
        assert 'The UEFI has been detected but' in err


def test_get_efi_device(monkeypatch):
    monkeypatch.setattr(partitions, 'run', RunMocked())
    monkeypatch.setattr(efi, 'get_efi_partition', lambda: EFI_PARTITION)

    assert efi.get_efi_device() == EFI_DEVICE


def test_EFIBootInfo_fail_not_efi(monkeypatch):
    monkeypatch.setattr(efi, 'is_efi', lambda: False)

    with pytest.raises(StopActorExecution) as err:
        efi.EFIBootInfo()
        assert 'Unable to collect data about UEFI on a BIOS system.' in err


def test_EFIBootInfo_fail_efibootmgr_error(monkeypatch):
    monkeypatch.setattr(efi, 'is_efi', lambda: True)
    monkeypatch.setattr(efi, 'run', RunMocked(raise_err=True))

    with pytest.raises(StopActorExecution) as err:
        efi.EFIBootInfo()
        assert 'Unable to get information about UEFI boot entries.' in err


def test_EFIBootInfo_success(monkeypatch):
    monkeypatch.setattr(efi, 'is_efi', lambda: True)
    monkeypatch.setattr(efi, 'run', RunMocked())

    efibootinfo = efi.EFIBootInfo()
    assert efibootinfo.current_bootnum == '0006'
    assert efibootinfo.next_bootnum is None
    assert efibootinfo.boot_order == ('0003', '0004', '0001', '0006', '0000', '0002', '0007', '0005')
    assert efibootinfo.entries == EFIBOOTMGR_OUTPUT_ENTRIES
