import os
from unittest import mock

import pytest

from leapp.libraries.common import grub, mdraid, partitions
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import DefaultGrub, DefaultGrubInfo
from leapp.utils.deprecation import suppress_deprecation

BOOT_PARTITION = '/dev/vda2'
BOOT_DEVICE = '/dev/vda'

MD_BOOT_DEVICE = '/dev/md0'
MD_BOOT_DEVICES_WITH_GRUB = ['/dev/sda', '/dev/sdb']

VALID_DD = b'GRUB GeomHard DiskRead Error'
INVALID_DD = b'Nothing to see here!'

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def raise_call_error(args=None):
    raise CalledProcessError(
        message='A Leapp Command Error occurred.',
        command=args,
        result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': 'fake', 'stderr': 'fake'}
    )


class RunMocked:

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
            else:
                raise ValueError('Invalid argument {}'.format(directory))

        elif self.args == ['lsblk', '-spnlo', 'name', BOOT_PARTITION]:
            stdout = BOOT_DEVICE
        elif self.args[:-1] == ['lsblk', '-spnlo', 'name']:
            stdout = self.args[-1][:-1]
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


# this as well as close_mocked is required, note the difference between open
# and os.open in open_mocked
def read_mocked(f, size):
    return f.read(size)


def close_mocked(f):
    f.close()


@suppress_deprecation(grub.get_grub_device)
def test_get_grub_device_library(monkeypatch):
    run_mocked = RunMocked()
    monkeypatch.setattr(partitions, 'run', run_mocked)
    monkeypatch.setattr(os, 'open', open_mocked)
    monkeypatch.setattr(os, 'read', read_mocked)
    monkeypatch.setattr(os, 'close', close_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    result = grub.get_grub_device()
    assert partitions.run.called == 2
    assert BOOT_DEVICE == result
    assert not api.current_logger.warnmsg
    assert 'GRUB is installed on {}'.format(result) in api.current_logger.infomsg


@suppress_deprecation(grub.get_grub_device)
def test_get_grub_device_fail_library(monkeypatch):
    # TODO(pstodulk): cover here also case with OSError (covered now in actors,
    # so keeping for the future when we have a time)
    run_mocked = RunMocked(raise_err=True)
    monkeypatch.setattr(partitions, 'run', run_mocked)
    monkeypatch.setattr(os, 'open', open_mocked)
    monkeypatch.setattr(os, 'read', read_mocked)
    monkeypatch.setattr(os, 'close', close_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    with pytest.raises(partitions.StorageScanError):
        grub.get_grub_device()
    assert partitions.run.called == 1
    err = 'Could not get name of underlying /boot partition'
    assert err in api.current_logger.warnmsg


@suppress_deprecation(grub.get_grub_device)
def test_device_no_grub_library(monkeypatch):
    run_mocked = RunMocked()
    monkeypatch.setattr(partitions, 'run', run_mocked)
    monkeypatch.setattr(os, 'open', open_invalid)
    monkeypatch.setattr(os, 'read', read_mocked)
    monkeypatch.setattr(os, 'close', close_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    result = grub.get_grub_device()
    assert partitions.run.called == 2
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
    monkeypatch.setattr(partitions, 'run', run_mocked)
    monkeypatch.setattr(os, 'open', open_mocked)
    monkeypatch.setattr(os, 'read', read_mocked)
    monkeypatch.setattr(os, 'close', close_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(mdraid, 'is_mdraid_dev', is_mdraid_dev_mocked)

    result = grub.get_grub_devices()
    assert partitions.run.called == 2
    assert [BOOT_DEVICE] == result
    assert not api.current_logger.warnmsg
    assert 'GRUB is installed on {}'.format(",".join(result)) in api.current_logger.infomsg


@pytest.mark.parametrize(
    'mock_dev, expect', [('grub_valid', True), ('grub_invalid', False)]
)
def test_has_grub(monkeypatch, mock_dev, expect):
    orig_open = os.open

    def open_mocked(path, flags):
        assert path == '/dev/sda1'
        return orig_open(os.path.join(CUR_DIR, mock_dev), flags)

    monkeypatch.setattr(os, 'open', open_mocked)
    assert expect == grub.has_grub('/dev/sda1')


@pytest.mark.parametrize('where', ['open', 'read'])
def test_has_grub_fail(monkeypatch, where):
    def raise_oserror(*args):
        raise OSError()

    monkeypatch.setattr(os, where, raise_oserror)

    with pytest.raises(OSError):
        grub.has_grub('/dev/sda1')


@pytest.mark.parametrize(
    'component_devs,expected',
    [
        (['/dev/sda1', '/dev/sdb1'], MD_BOOT_DEVICES_WITH_GRUB),
        (['/dev/sda1', '/dev/sdb1', '/dev/sdc1', '/dev/sdd1'], MD_BOOT_DEVICES_WITH_GRUB),
        (['/dev/sda2', '/dev/sdc1'], ['/dev/sda']),
        (['/dev/sdd3', '/dev/sdb2'], ['/dev/sdb']),
    ]
)
def test_get_grub_devices_raid_device(component_devs, expected):
    with mock.patch('leapp.libraries.common.grub.get_boot_partition') as mock_get_boot_part, \
         mock.patch('leapp.libraries.common.grub.has_grub') as mock_has_grub, \
         mock.patch('leapp.libraries.common.mdraid.is_mdraid_dev') as mock_is_mdraid_dev, \
         mock.patch('leapp.libraries.common.mdraid.get_component_devices') as mock_get_component_devs, \
         mock.patch('leapp.libraries.common.partitions.blk_dev_from_partition') as mock_blk_dev_from_part:

        mock_get_boot_part.return_value = MD_BOOT_DEVICE
        mock_is_mdraid_dev.return_value = True
        mock_get_component_devs.return_value = component_devs
        mock_blk_dev_from_part.side_effect = lambda dev: dev[:-1]
        mock_has_grub.side_effect = lambda dev: dev in expected

        ret = grub.get_grub_devices()

        mock_is_mdraid_dev.assert_called_once_with(MD_BOOT_DEVICE)
        mock_get_component_devs.assert_called_once_with(MD_BOOT_DEVICE)
        mock_blk_dev_from_part.assert_has_calls(
            [mock.call(dev) for dev in component_devs], any_order=True
        )
        mock_has_grub.assert_has_calls(
            [mock.call(dev) for dev in expected], any_order=True
        )
        assert ret == expected


@pytest.mark.parametrize(
    'component_devs,expected',
    [
        (['/dev/sda1', '/dev/sdb1'], MD_BOOT_DEVICES_WITH_GRUB),
        (['/dev/sda1', '/dev/sdb1', '/dev/sdc1', '/dev/sdd1'], MD_BOOT_DEVICES_WITH_GRUB),
        (['/dev/sda2', '/dev/sdc1'], ['/dev/sda']),
        (['/dev/sdd3', '/dev/sdb2'], ['/dev/sdb']),
    ]
)
def test_get_grub_devices_fail(component_devs, expected):
    """
    Test that all the possibly exceptions are caught.
    """
    with mock.patch('leapp.libraries.common.grub.get_boot_partition') as mock_get_boot_part, \
         mock.patch('leapp.libraries.common.grub.has_grub') as mock_has_grub, \
         mock.patch('leapp.libraries.common.mdraid.is_mdraid_dev') as mock_is_mdraid_dev, \
         mock.patch('leapp.libraries.common.mdraid.get_component_devices') as mock_get_component_devs, \
         mock.patch('leapp.libraries.common.partitions.blk_dev_from_partition') as mock_blk_dev_from_part:

        mock_get_boot_part.side_effect = partitions.StorageScanError
        mock_is_mdraid_dev.return_value = True
        mock_get_component_devs.return_value = component_devs
        mock_blk_dev_from_part.side_effect = lambda dev: dev[:-1]
        mock_has_grub.side_effect = lambda dev: dev in expected

        with pytest.raises(grub.GRUBDeviceError):
            grub.get_grub_devices()

        mock_get_boot_part.return_value = MD_BOOT_DEVICE
        mock_is_mdraid_dev.side_effect = CalledProcessError

        with pytest.raises(grub.GRUBDeviceError):
            grub.get_grub_devices()

        mock_is_mdraid_dev.return_value = True
        mock_blk_dev_from_part.side_effect = partitions.StorageScanError

        with pytest.raises(grub.GRUBDeviceError):
            grub.get_grub_devices()

        mock_blk_dev_from_part.return_value = component_devs
        mock_has_grub.side_effect = OSError

        with pytest.raises(grub.GRUBDeviceError):
            grub.get_grub_devices()
