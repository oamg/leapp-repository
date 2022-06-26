import pytest

from leapp import reporting
from leapp.libraries.actor.checkyumpluginsenabled import check_required_yum_plugins_enabled
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import PkgManagerInfo
from leapp.utils.report import is_inhibitor


def _create_report_with_multiple_base_list_primitive_fields():
    report_fields = [
            reporting.Title('a title'),
            reporting.Summary('some summary'),
            reporting.RelatedResource('file', '/path/to/some/configA'),
            reporting.RelatedResource('file', '/path/to/some/configB'),
            reporting.RelatedResource('file', '/path/to/some/configC'),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.REPOSITORY])]
    reporting.create_report(report_fields)


def test__create_report_mocked(monkeypatch):
    actor_reports = create_report_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(reporting, 'create_report', actor_reports)
    _create_report_with_multiple_base_list_primitive_fields()

    # make sure that all related resources are present
    for config in ['/path/to/some/configA', '/path/to/some/configB', '/path/to/some/configC']:
        assert config in [rr['title'] for rr in actor_reports.report_fields['detail']['related_resources']]

    # make sure that tags/flags joined as groups are present under groups
    for group in [reporting.Groups.INHIBITOR, reporting.Groups.REPOSITORY]:
        assert group in actor_reports.report_fields['groups']


def test_report_when_missing_required_plugins(monkeypatch):
    """Test whether a report entry is created when any of the required YUM plugins are missing."""
    yum_config = PkgManagerInfo(enabled_plugins=['product-id', 'some-user-plugin'])

    actor_reports = create_report_mocked()

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(reporting, 'create_report', actor_reports)

    check_required_yum_plugins_enabled(yum_config)

    assert actor_reports.called, "Report wasn't created when required a plugin is missing."

    fail_description = 'The missing required plugin is not mentioned in the report.'
    assert 'subscription-manager' in actor_reports.report_fields['summary'], fail_description

    fail_description = 'The upgrade should be inhibited when plugins are not enabled.'
    assert is_inhibitor(actor_reports.report_fields), fail_description


def test_nothing_is_reported_when_rhsm_disabled(monkeypatch):
    actor_mocked = CurrentActorMocked(envars={'LEAPP_NO_RHSM': '1'})

    monkeypatch.setattr(api, 'current_actor', actor_mocked)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    yum_config = PkgManagerInfo(enabled_plugins=[])
    check_required_yum_plugins_enabled(yum_config)

    assert not reporting.create_report.called, 'Report was created even if LEAPP_NO_RHSM was set'
