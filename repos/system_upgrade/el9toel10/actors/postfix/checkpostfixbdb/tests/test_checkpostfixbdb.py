import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import checkpostfixbdb
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import PostfixBdbConfiguration


def test_process_no_msg(monkeypatch):
    def consume_mocked(*args, **kwargs):
        yield None

    monkeypatch.setattr(api, 'consume', consume_mocked)

    with pytest.raises(StopActorExecutionError):
        checkpostfixbdb.process()


def test_process_postfix_absent(monkeypatch):
    def consume_mocked(*args, **kwargs):
        yield PostfixBdbConfiguration(postfix_present=False, bdb_occurrences=[])

    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'consume', consume_mocked)

    checkpostfixbdb.process()
    assert 'postfix package not found' in ''.join(api.current_logger.dbgmsg)
    assert reporting.create_report.called == 0


def test_process_already_lmdb(monkeypatch):
    def consume_mocked(*args, **kwargs):
        yield PostfixBdbConfiguration(postfix_present=True, bdb_occurrences=[])

    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'consume', consume_mocked)

    checkpostfixbdb.process()
    assert 'no hash:/btree:' in ''.join(api.current_logger.dbgmsg)
    assert reporting.create_report.called == 0


def test_process_hash_maps_reported(monkeypatch):
    findings = [
        '/etc/postfix/main.cf: alias_maps = hash:/etc/aliases',
        '/etc/postfix/main.cf: default_database_type = hash',
    ]

    def consume_mocked(*args, **kwargs):
        yield PostfixBdbConfiguration(postfix_present=True, bdb_occurrences=findings)

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'consume', consume_mocked)

    checkpostfixbdb.process()
    assert reporting.create_report.called == 1
    report = reporting.create_report.reports[0]
    assert 'Berkeley DB' in report['title']
    summary = report['summary']
    assert 'alias_maps = hash:/etc/aliases' in summary
    assert 'default_database_type = hash' in summary
    assert checkpostfixbdb.REPORT_KCS_URL in str(report)
