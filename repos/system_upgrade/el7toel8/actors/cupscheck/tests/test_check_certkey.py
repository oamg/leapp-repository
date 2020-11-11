import pytest

from leapp import reporting
from leapp.libraries.actor.cupscheck import check_certkey_directives
from leapp.libraries.common.testutils import create_report_mocked
from leapp.models import CupsChangedFeatures


@pytest.mark.parametrize("certkey_exists,n_reports", [(False, 0), (True, 1)])
def test_check_certkey_directives(certkey_exists, n_reports):
    facts = CupsChangedFeatures(certkey=certkey_exists)
    report_func = create_report_mocked()

    check_certkey_directives(facts, report_func)

    assert report_func.called == n_reports

    if report_func.called:
        report_fields = report_func.report_fields

        assert 'ServerKey/ServerCertificate directives' in report_fields['title']
        assert report_fields['severity'] == reporting.Severity.MEDIUM
