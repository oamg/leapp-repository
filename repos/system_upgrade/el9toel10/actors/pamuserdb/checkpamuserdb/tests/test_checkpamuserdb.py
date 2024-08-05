import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import checkpamuserdb
from leapp.libraries.common.testutils import create_report_mocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import PamUserDbLocation


def test_process_no_msg(monkeypatch):
    def consume_mocked(*args, **kwargs):
        yield None

    monkeypatch.setattr(api, 'consume', consume_mocked)

    with pytest.raises(StopActorExecutionError):
        checkpamuserdb.process()


def test_process_no_location(monkeypatch):
    def consume_mocked(*args, **kwargs):
        yield PamUserDbLocation(locations=[])

    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'consume', consume_mocked)

    checkpamuserdb.process()
    assert (
        'No pam_userdb databases were located, thus nothing will be converted'
        in api.current_logger.dbgmsg
    )


def test_process_locations(monkeypatch):
    def consume_mocked(*args, **kwargs):
        yield PamUserDbLocation(locations=['/tmp/db1', '/tmp/db2'])

    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    monkeypatch.setattr(api, 'consume', consume_mocked)

    checkpamuserdb.process()
    assert reporting.create_report.called == 1
