import os

import pytest

from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.actor import library
from leapp import reporting
from leapp.libraries.common.testutils import produce_mocked, create_report_mocked
from leapp.libraries.stdlib import api
from leapp.models import OSReleaseFacts

SUPPORTED_VERSION = {'rhel': ['7.5', '7.6']}


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


def test_no_facts(monkeypatch):
    def os_release_mocked(*models):
        yield None

    monkeypatch.setattr(api, "consume", os_release_mocked)
    with pytest.raises(StopActorExecutionError):
        library.check_os_version(SUPPORTED_VERSION)


def create_os_release(release_id, version_id=7.6):
    return OSReleaseFacts(
        release_id=release_id,
        name='test',
        pretty_name='test {}'.format(version_id),
        version='Some Test {}'.format(version_id),
        version_id=version_id,
        variant=None,
        variant_id=None,
    )


def test_not_supported_id(monkeypatch):
    def os_release_mocked(*models):
        yield create_os_release('rhel', '7.7')

    monkeypatch.setattr(api, "consume", os_release_mocked)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    library.check_os_version(SUPPORTED_VERSION)
    assert reporting.create_report.called == 1
    assert 'Unsupported OS version' in reporting.create_report.report_fields['title']
    assert 'flags' in reporting.create_report.report_fields
    assert 'inhibitor' in reporting.create_report.report_fields['flags']


def test_not_supported_release(monkeypatch):
    def os_release_mocked(*models):
        yield create_os_release('unsupported', SUPPORTED_VERSION['rhel'][0])

    monkeypatch.setattr(api, "consume", os_release_mocked)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    library.check_os_version(SUPPORTED_VERSION)
    assert reporting.create_report.called == 1
    assert 'Unsupported OS' in reporting.create_report.report_fields['title']
    assert 'flags' in reporting.create_report.report_fields
    assert 'inhibitor' in reporting.create_report.report_fields['flags']


def test_supported_release(monkeypatch):
    def os_mocked_first_release(*models):
        yield create_os_release('rhel', SUPPORTED_VERSION['rhel'][0])

    def os_mocked_second_release(*models):
        yield create_os_release('rhel', SUPPORTED_VERSION['rhel'][1])

    monkeypatch.setattr(api, "consume", os_mocked_first_release)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    library.check_os_version(SUPPORTED_VERSION)
    monkeypatch.setattr(api, "consume", os_mocked_second_release)
    library.check_os_version(SUPPORTED_VERSION)
    assert reporting.create_report.called == 0


def test_invalid_versions(monkeypatch):
    def os_release_mocked(*models):
        yield create_os_release('rhel', '7.6')

    monkeypatch.setattr(api, "consume", os_release_mocked)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    with pytest.raises(StopActorExecution):
        library.check_os_version('string')
    with pytest.raises(StopActorExecution):
        library.check_os_version(None)

    library.check_os_version({})
    assert reporting.create_report.called == 1
    with pytest.raises(StopActorExecutionError):
        library.check_os_version({'rhel': None})
