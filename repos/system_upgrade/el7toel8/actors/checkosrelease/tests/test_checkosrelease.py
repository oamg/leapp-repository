import os

from leapp import reporting
from leapp.libraries.actor import checkosrelease
from leapp.libraries.common.config import version
from leapp.libraries.common.testutils import (
    create_report_mocked,
    produce_mocked,
)


def test_skip_check(monkeypatch):
    monkeypatch.setattr(os, "getenv", lambda _unused: True)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    assert checkosrelease.skip_check()
    assert reporting.create_report.called == 1
    assert 'Skipped OS release check' in reporting.create_report.report_fields['title']
    assert reporting.create_report.report_fields['severity'] == 'high'
    assert 'inhibitor' not in reporting.create_report.report_fields['groups']


def test_no_skip_check(monkeypatch):
    monkeypatch.setattr(os, "getenv", lambda _unused: False)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    assert not checkosrelease.skip_check()
    assert reporting.create_report.called == 0


def test_not_supported_release(monkeypatch):
    monkeypatch.setattr(version, "is_supported_version", lambda: False)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    checkosrelease.check_os_version()
    assert reporting.create_report.called == 1
    assert 'The installed OS version is not supported' in reporting.create_report.report_fields['title']
    assert 'groups' in reporting.create_report.report_fields
    assert 'inhibitor' in reporting.create_report.report_fields['groups']


def test_supported_release(monkeypatch):
    monkeypatch.setattr(version, "is_supported_version", lambda: True)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    checkosrelease.check_os_version()
    assert reporting.create_report.called == 0
