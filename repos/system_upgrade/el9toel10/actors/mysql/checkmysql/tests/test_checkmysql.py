import pytest

from leapp import reporting
from leapp.libraries.actor import checkmysql
from leapp.libraries.common.testutils import create_report_mocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import MySQLConfiguration, Report
from leapp.exceptions import StopActorExecutionError


def _find_hint(report: dict) -> str | None:
    r = None
    for remedy in report['detail']['remediations']:
        if remedy['type'] == 'hint':
            r = remedy['context']
            break
    return r


def test_process_no_msg(monkeypatch):
    def consume_mocked(*args, **kwargs):
        yield None

    monkeypatch.setattr(api, 'consume', consume_mocked)

    with pytest.raises(StopActorExecutionError):
        checkmysql.process()


def test_process_no_mysql(monkeypatch):
    def consume_mocked(*args, **kwargs):
        yield MySQLConfiguration(mysql_present=False,
                                 removed_options=[],
                                 removed_arguments=[])

    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    monkeypatch.setattr(api, 'consume', consume_mocked)

    checkmysql.process()
    assert (
        'mysql-server package not found, no report generated'
        in api.current_logger.dbgmsg
    )
    assert len(reporting.create_report.reports) == 0


def test_process_no_deprecated(monkeypatch):
    def consume_mocked(*args, **kwargs):
        yield MySQLConfiguration(mysql_present=True,
                                 removed_options=[],
                                 removed_arguments=[])

    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    monkeypatch.setattr(api, 'consume', consume_mocked)

    checkmysql.process()

    # Check that we have made a report
    assert len(reporting.create_report.reports) == 1

    r = _find_hint(reporting.create_report.reports[0])

    # Check that Hint was in the report
    assert r is not None

    assert ('Following configuration options won\'t work on a new version'
            not in r)


def test_process_deprecated(monkeypatch):
    def consume_mocked(*args, **kwargs):
        yield MySQLConfiguration(mysql_present=True,
                                 removed_options=['avoid_temporal_upgrade', '--old'],
                                 removed_arguments=['--language'])

    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    monkeypatch.setattr(api, 'consume', consume_mocked)

    checkmysql.process()

    # Check that we have made a report
    assert len(reporting.create_report.reports) == 1

    # Find first hint message in remediations
    r = _find_hint(reporting.create_report.reports[0])

    # Check that Hint was in the report
    assert r is not None

    # Check that we informed user about all the deprecated options
    assert 'avoid_temporal_upgrade' in r
    assert '--old' in r
    assert '--language' in r
