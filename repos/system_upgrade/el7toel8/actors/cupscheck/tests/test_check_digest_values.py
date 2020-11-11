import pytest

from leapp import reporting
from leapp.libraries.actor.cupscheck import check_digest_values
from leapp.libraries.common.testutils import create_report_mocked
from leapp.models import CupsChangedFeatures


@pytest.mark.parametrize("digest_exists,n_reports", [(False, 0), (True, 1)])
def test_check_digest_values(digest_exists, n_reports):
    facts = CupsChangedFeatures(digest=digest_exists)
    report_func = create_report_mocked()

    check_digest_values(facts, report_func)

    assert report_func.called == n_reports

    if report_func.called:
        report_fields = report_func.report_fields

        assert 'no longer supports Digest' in report_fields['title']
        assert report_fields['severity'] == reporting.Severity.MEDIUM
