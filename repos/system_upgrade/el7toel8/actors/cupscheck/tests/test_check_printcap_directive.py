import pytest

from leapp import reporting
from leapp.libraries.actor.cupscheck import check_printcap_directive
from leapp.libraries.common.testutils import create_report_mocked
from leapp.models import CupsChangedFeatures


@pytest.mark.parametrize("printcap_exists,n_reports", [(False, 0), (True, 1)])
def test_check_printcap_directive(printcap_exists, n_reports):
    facts = CupsChangedFeatures(printcap=printcap_exists)
    report_func = create_report_mocked()

    check_printcap_directive(facts, report_func)

    assert report_func.called == n_reports

    if report_func.called:
        report_fields = report_func.report_fields

        assert 'PrintcapFormat directive' in report_fields['title']
        assert report_fields['severity'] == reporting.Severity.LOW
