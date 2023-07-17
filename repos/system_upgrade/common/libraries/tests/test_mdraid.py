import os

import pytest

from leapp.libraries.common import mdraid
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError

MD_DEVICE = '/dev/md0'
NOT_MD_DEVICE = '/dev/sda'

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def raise_call_error(args=None):
    raise CalledProcessError(
        message='A Leapp Command Error occurred.',
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

        if self.args == ['mdadm', '--query', MD_DEVICE]:
            stdout = '/dev/md0: 1022.00MiB raid1 2 devices, 0 spares. Use mdadm --detail for more detail.'
        elif self.args == ['mdadm', '--query', NOT_MD_DEVICE]:
            stdout = '/dev/sda: is not an md array'

        elif self.args == ['mdadm', '--detail', '--verbose', '--brief', MD_DEVICE]:
            stdout = 'ARRAY /dev/md0 level=raid1 num-devices=2 metadata=1.2 name=localhost.localdomain:0 UUID=c4acea6e:d56e1598:91822e3f:fb26832c\n    devices=/dev/sda1,/dev/sdb1'  # noqa: E501; pylint: disable=line-too-long
        elif self.args == ['mdadm', '--detail', '--verbose', '--brief', NOT_MD_DEVICE]:
            stdout = 'mdadm: /dev/sda does not appear to be an md device'

        return {'stdout': stdout}


@pytest.mark.parametrize('dev,expected', [(MD_DEVICE, True), (NOT_MD_DEVICE, False)])
def test_is_mdraid_dev(monkeypatch, dev, expected):
    run_mocked = RunMocked()
    monkeypatch.setattr(mdraid, 'run', run_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(os.path, 'exists', lambda dummy: True)

    result = mdraid.is_mdraid_dev(dev)
    assert mdraid.run.called == 1
    assert expected == result
    assert not api.current_logger.warnmsg


def test_is_mdraid_dev_error(monkeypatch):
    run_mocked = RunMocked(raise_err=True)
    monkeypatch.setattr(mdraid, 'run', run_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(os.path, 'exists', lambda dummy: True)

    with pytest.raises(CalledProcessError) as err:
        mdraid.is_mdraid_dev(MD_DEVICE)

    assert mdraid.run.called == 1
    expect_msg = 'Could not check if device "{}" is an md device:'.format(MD_DEVICE)
    assert expect_msg in err.value.message


def test_is_mdraid_dev_notool(monkeypatch):
    run_mocked = RunMocked(raise_err=True)
    monkeypatch.setattr(mdraid, 'run', run_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(os.path, 'exists', lambda dummy: False)

    result = mdraid.is_mdraid_dev(MD_DEVICE)
    assert not result
    assert not mdraid.run.called
    assert api.current_logger.warnmsg


def test_get_component_devices_ok(monkeypatch):
    run_mocked = RunMocked()
    monkeypatch.setattr(mdraid, 'run', run_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    result = mdraid.get_component_devices(MD_DEVICE)
    assert mdraid.run.called == 1
    assert ['/dev/sda1', '/dev/sdb1'] == result
    assert not api.current_logger.warnmsg


def test_get_component_devices_not_md_device(monkeypatch):
    run_mocked = RunMocked()
    monkeypatch.setattr(mdraid, 'run', run_mocked)

    with pytest.raises(ValueError) as err:
        mdraid.get_component_devices(NOT_MD_DEVICE)

    assert mdraid.run.called == 1
    expect_msg = 'Expected md device, but got: {}'.format(NOT_MD_DEVICE)
    assert expect_msg in str(err.value)
