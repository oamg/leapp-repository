import pytest

from leapp import reporting
from leapp.libraries.actor.cupscheck import check_interface_scripts
from leapp.libraries.common.testutils import create_report_mocked
from leapp.models import CupsChangedFeatures


@pytest.mark.parametrize("interface_exists,n_reports", [(False, 0), (True, 1)])
def test_check_interface_scripts(interface_exists, n_reports):
    facts = CupsChangedFeatures(interface=interface_exists)
    report_func = create_report_mocked()

    check_interface_scripts(facts, report_func)

    assert report_func.called == n_reports

    if report_func.called:
        report_fields = report_func.report_fields

        assert 'usage of interface scripts' in report_fields['title']
        assert 'Interface scripts are no longer' in report_fields['summary']
        assert report_fields['severity'] == reporting.Severity.MEDIUM
        assert all('*cupsFilter2' in r['context']
                   for r in report_fields['detail']['remediations'])
