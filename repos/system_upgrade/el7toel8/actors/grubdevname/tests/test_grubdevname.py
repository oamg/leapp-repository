import os

import pytest

from leapp.exceptions import StopActorExecution
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.libraries.common import testutils
from leapp.libraries.actor import library


BOOT_PARTITION = '/dev/vda1'

BOOT_DEVICE = '/dev/vda'
BOOT_DEVICE_ENV = '/dev/sda'

VALID_DD = b'GRUB GeomHard DiskRead Error'
INVALID_DD = b'Nothing here'


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
    return open('tests/valid' if fn == BOOT_DEVICE else 'tests/invalid', 'r')


def open_invalid(fn, flags):
    return open('tests/invalid', 'r')


def read_mocked(f, size):
    return f.read(size)


def close_mocked(f):
    f.close()


def test_get_grub_device(monkeypatch):
    run_mocked = RunMocked()
    monkeypatch.setattr(library, 'run', run_mocked)
    monkeypatch.setattr(api, 'produce', testutils.produce_mocked())
    monkeypatch.setattr(os, 'open', open_mocked)
    monkeypatch.setattr(os, 'read', read_mocked)
    monkeypatch.setattr(os, 'close', close_mocked)
    library.get_grub_device()
    assert library.run.called == 2
    assert BOOT_DEVICE == api.produce.model_instances[0].grub_device


def test_get_grub_device_fail(monkeypatch):
    run_mocked = RunMocked(raise_err=True)
    monkeypatch.setattr(library, 'run', run_mocked)
    monkeypatch.setattr(api, 'produce', testutils.produce_mocked())
    monkeypatch.setattr(os, 'open', open_mocked)
    monkeypatch.setattr(os, 'read', read_mocked)
    monkeypatch.setattr(os, 'close', close_mocked)
    with pytest.raises(StopActorExecution):
        library.get_grub_device()
    assert library.run.called == 1
    assert not api.produce.model_instances


def test_grub_device_env_var(monkeypatch):
    run_mocked = RunMocked()
    monkeypatch.setenv('LEAPP_GRUB_DEVICE', BOOT_DEVICE_ENV)
    monkeypatch.setattr(library, 'run', run_mocked)
    monkeypatch.setattr(api, 'produce', testutils.produce_mocked())
    monkeypatch.setattr(os, 'open', open_mocked)
    monkeypatch.setattr(os, 'read', read_mocked)
    monkeypatch.setattr(os, 'close', close_mocked)
    library.get_grub_device()
    assert library.run.called == 0
    assert BOOT_DEVICE_ENV == api.produce.model_instances[0].grub_device


def test_device_no_grub(monkeypatch):
    run_mocked = RunMocked()
    monkeypatch.setattr(library, 'run', run_mocked)
    monkeypatch.setattr(api, 'produce', testutils.produce_mocked())
    monkeypatch.setattr(os, 'open', open_invalid)
    monkeypatch.setattr(os, 'read', read_mocked)
    monkeypatch.setattr(os, 'close', close_mocked)
    library.get_grub_device()
    assert library.run.called == 2
    assert not api.produce.model_instances
