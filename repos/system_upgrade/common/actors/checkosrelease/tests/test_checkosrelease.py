import os

from leapp import reporting
from leapp.libraries.actor import checkosrelease
from leapp.libraries.common.config import version
from leapp.libraries.common.testutils import create_report_mocked, produce_mocked
from leapp.utils.report import is_inhibitor


def test_skip_check(monkeypatch):
    monkeypatch.setenv('LEAPP_DEVEL_SKIP_CHECK_OS_RELEASE', '1')
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    assert checkosrelease.skip_check()
    assert reporting.create_report.called == 1
    assert 'Skipped OS release check' in reporting.create_report.report_fields['title']
    assert reporting.create_report.report_fields['severity'] == 'high'


def test_no_skip_check(monkeypatch):
    monkeypatch.delenv('LEAPP_DEVEL_SKIP_CHECK_OS_RELEASE', raising=False)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    assert not checkosrelease.skip_check()
    assert reporting.create_report.called == 0


def test_not_supported_release(monkeypatch):
    monkeypatch.setattr(version, "is_supported_version", lambda: False)
    monkeypatch.setattr(version, "get_source_major_version", lambda: '7')
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    checkosrelease.check_os_version()
    assert reporting.create_report.called == 1
    assert 'The installed OS version is not supported' in reporting.create_report.report_fields['title']
    assert is_inhibitor(reporting.create_report.report_fields)


def test_supported_release(monkeypatch):
    monkeypatch.setattr(version, "is_supported_version", lambda: True)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    checkosrelease.check_os_version()
    assert reporting.create_report.called == 0
