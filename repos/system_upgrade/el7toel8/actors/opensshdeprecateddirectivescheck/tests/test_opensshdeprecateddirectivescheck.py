import pytest

from leapp import reporting
from leapp.libraries.actor.opensshdeprecateddirectivescheck import inhibit_if_deprecated_directives_used
from leapp.libraries.common.testutils import create_report_mocked, logger_mocked
from leapp.models import OpenSshConfig
from leapp.utils.report import is_inhibitor


def test_inhibit_if_deprecated_directives_used(monkeypatch):
    """Tests whether the upgrade is inhibited when deprecated directives are used in config."""
    created_report = create_report_mocked()
    monkeypatch.setattr(reporting, 'create_report', created_report)

    ssh_config = OpenSshConfig(
        permit_root_login=[],
        deprecated_directives=['ShowPatchLevel']
    )

    inhibit_if_deprecated_directives_used(ssh_config)

    fail_description = 'Report entry was not created when deprecated directive found in the ssh config.'
    assert created_report.called == 1, fail_description

    fail_description = 'Report doesn\'t have information about deprecated directive in the title.'
    assert 'deprecated directive' in created_report.report_fields['title'].lower(), fail_description

    fail_description = 'Report doesn\'t contain the (mocked) deprecated directive present in the config.'
    # The report should have the directive in a preserved form (same as found in configuration)
    assert 'ShowPatchLevel' in created_report.report_fields['summary'], fail_description

    assert created_report.report_fields['severity'] == 'high', 'Report has incorrect severity.'

    fail_description = 'Report should have the inhibition flag set when deprecated directive is present.'
    assert is_inhibitor(created_report.report_fields), fail_description

    assert created_report.report_fields['detail']['remediations'], 'Report should carry some remediation information.'


def test_inhibit_if_deprecated_directives_used_no_deprecated_directives(monkeypatch):
    """Tests whether the upgrade is not inhibited when no deprecated directives are used in config."""
    created_report = create_report_mocked()
    monkeypatch.setattr(reporting, 'create_report', created_report)

    ssh_config = OpenSshConfig(
        permit_root_login=[],
        deprecated_directives=[]
    )

    inhibit_if_deprecated_directives_used(ssh_config)
    assert created_report.called == 0, 'No report should be created if no deprecated directive present in the config.'
