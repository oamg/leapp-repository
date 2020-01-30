import os

import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.actor import library
from leapp.libraries.common.config import version
from leapp.libraries.common.testutils import (create_report_mocked,
                                              produce_mocked)
from leapp.libraries.stdlib import api


def test_skip_check(monkeypatch):
    monkeypatch.setattr(os, "getenv", lambda _unused: True)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    assert library.skip_check()
    assert reporting.create_report.called == 1
    assert 'Skipped OS release check' in reporting.create_report.report_fields['title']
    assert reporting.create_report.report_fields['severity'] == 'high'
    assert 'flags' not in reporting.create_report.report_fields


def test_no_skip_check(monkeypatch):
    monkeypatch.setattr(os, "getenv", lambda _unused: False)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    assert not library.skip_check()
    assert reporting.create_report.called == 0


def test_not_supported_release(monkeypatch):
    monkeypatch.setattr(version, "is_supported_version", lambda: False)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    library.check_os_version()
    assert reporting.create_report.called == 1
    assert 'Unsupported OS' in reporting.create_report.report_fields['title']
    assert 'flags' in reporting.create_report.report_fields
    assert 'inhibitor' in reporting.create_report.report_fields['flags']


def test_supported_release(monkeypatch):
    monkeypatch.setattr(version, "is_supported_version", lambda: True)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    library.check_os_version()
    assert reporting.create_report.called == 0
