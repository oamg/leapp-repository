import os

import pytest

from leapp.exceptions import StopActorExecution
from leapp.libraries.common import grub
from leapp.libraries.stdlib import CalledProcessError, api
from leapp.libraries.common.testutils import logger_mocked

BOOT_PARTITION = '/dev/vda1'
BOOT_DEVICE = '/dev/vda'

VALID_DD = b'GRUB GeomHard DiskRead Error'
INVALID_DD = b'Nothing to see here!'

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def raise_call_error(args=None):
    raise CalledProcessError(
        message='A Leapp Command Error occured.',
        command=args,
        result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': 'fake', 'stderr': 'fake'}
    )


class RunMocked(object):

    def __init__(self, raise_err=False):
        self.called = 0
        self.args = None
        self.raise_err = raise_err

    def __call__(self, args, encoding=None):
        self.called += 1
        self.args = args
        if self.raise_err:
            raise_call_error(args)

        if self.args == ['grub2-probe', '--target=device', '/boot']:
            stdout = BOOT_PARTITION

        elif self.args == ['lsblk', '-spnlo', 'name', BOOT_PARTITION]:
            stdout = BOOT_DEVICE

        return {'stdout': stdout}


def open_mocked(fn, flags):
    return open(
        os.path.join(CUR_DIR, 'grub_valid') if fn == BOOT_DEVICE else os.path.join(CUR_DIR, 'grub_invalid'), 'r'
    )


def open_invalid(fn, flags):
    return open(os.path.join(CUR_DIR, 'grub_invalid'), 'r')


def read_mocked(f, size):
    return f.read(size)


def close_mocked(f):
    f.close()


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


def test_get_grub_device_fail_library(monkeypatch):
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
