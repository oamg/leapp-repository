import pytest

from leapp import reporting
from leapp.libraries.actor.cupscheck import check_include_directive
from leapp.libraries.common.testutils import create_report_mocked
from leapp.models import CupsChangedFeatures


@pytest.mark.parametrize("include_exists,n_reports", [(False, 0), (True, 1)])
def test_check_include_directive(include_exists, n_reports):
    facts = CupsChangedFeatures(include=include_exists,
                                include_files=['/etc/cups/cupsd.conf'])
    report_func = create_report_mocked()

    check_include_directive(facts, report_func)

    assert report_func.called == n_reports

    if report_func.called:
        report_fields = report_func.report_fields

        assert 'no longer supports usage of Include' in report_fields['title']
        assert report_fields['severity'] == reporting.Severity.MEDIUM
