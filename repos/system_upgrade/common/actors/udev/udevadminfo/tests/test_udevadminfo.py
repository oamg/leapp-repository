import os

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import udevadminfo
from leapp.libraries.common import testutils
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import UdevAdmInfoData

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def _raise_call_error(*args):
    raise CalledProcessError(
        message='A Leapp Command Error occurred.',
        command=args,
        result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': 'fake', 'stderr': 'fake'}
    )


def test_failed_run(monkeypatch):
    monkeypatch.setattr(api, 'produce', testutils.produce_mocked())
    monkeypatch.setattr(udevadminfo, 'run', _raise_call_error)

    with pytest.raises(StopActorExecutionError):
        udevadminfo.process()


def test_udevadminfo(monkeypatch):

    with open(os.path.join(CUR_DIR, 'files', 'udevadm_database'), 'r') as fp:
        mocked_data = fp.read()
    monkeypatch.setattr(api, 'produce', testutils.produce_mocked())
    monkeypatch.setattr(udevadminfo, 'run', lambda *args: {'stdout': mocked_data})
    udevadminfo.process()

    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], UdevAdmInfoData)
    assert api.produce.model_instances[0].db == mocked_data
