from io import StringIO

import pytest

from leapp.libraries.actor import scanmachineid
from leapp.libraries.common.testutils import logger_mocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import MachineIdInfo

_VALID_MACHINE_ID = 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4'


@pytest.mark.parametrize('content,expected_id', [
    (_VALID_MACHINE_ID + '\n', _VALID_MACHINE_ID),
    (_VALID_MACHINE_ID, _VALID_MACHINE_ID),
    ('', ''),
    (_VALID_MACHINE_ID + ' \n', _VALID_MACHINE_ID + ' '),
    (' ' + _VALID_MACHINE_ID + '\n', ' ' + _VALID_MACHINE_ID),
])
def test_scan_machine_id(monkeypatch, content, expected_id):
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(scanmachineid, 'open', lambda *a, **kw: StringIO(content), raising=False)
    scanmachineid.process()
    assert api.produce.called == 1
    msg = api.produce.model_instances[0]
    assert isinstance(msg, MachineIdInfo)
    assert msg.machine_id == expected_id


def test_scan_machine_id_missing(monkeypatch):
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    def _raise_file_not_found(*args, **kwargs):
        raise FileNotFoundError('No such file or directory')

    monkeypatch.setattr(scanmachineid, 'open', _raise_file_not_found, raising=False)
    scanmachineid.process()
    assert api.produce.called == 1
    msg = api.produce.model_instances[0]
    assert isinstance(msg, MachineIdInfo)
    assert msg.machine_id is None
    assert api.current_logger.warnmsg


def test_scan_machine_id_unreadable(monkeypatch):
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    def _raise_os_error(*args, **kwargs):
        raise OSError('Permission denied')

    monkeypatch.setattr(scanmachineid, 'open', _raise_os_error, raising=False)
    scanmachineid.process()
    assert api.produce.called == 1
    msg = api.produce.model_instances[0]
    assert isinstance(msg, MachineIdInfo)
    assert msg.machine_id is None
    assert api.current_logger.warnmsg
