import os

import pytest

from leapp.exceptions import StopActorExecution
from leapp.libraries.common import grub, mdraid
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import DefaultGrub, DefaultGrubInfo
from leapp.utils.deprecation import suppress_deprecation

BOOT_PARTITION = '/dev/vda1'
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


class RunMocked(object):

    def __init__(self, raise_err=False, boot_on_raid=False):
        self.called = 0
        self.args = None
        self.raise_err = raise_err
        self.boot_on_raid = boot_on_raid

    def __call__(self, args, encoding=None):
        self.called += 1
        self.args = args
        if self.raise_err:
            raise_call_error(args)

        if self.args == ['grub2-probe', '--target=device', '/boot']:
            stdout = MD_BOOT_DEVICE if self.boot_on_raid else BOOT_PARTITION

        elif self.args == ['lsblk', '-spnlo', 'name', BOOT_PARTITION]:
            stdout = BOOT_DEVICE
        elif self.args[:-1] == ['lsblk', '-spnlo', 'name']:
            stdout = self.args[-1][:-1]

        return {'stdout': stdout}


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
