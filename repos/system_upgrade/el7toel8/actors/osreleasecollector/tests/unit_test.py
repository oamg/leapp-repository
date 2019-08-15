from leapp.libraries.actor.library import get_os_release_info
from leapp import reporting
from leapp.libraries.common.testutils import produce_mocked, create_report_mocked
from leapp.models import OSReleaseFacts


def test_get_os_release_info(monkeypatch):
    monkeypatch.setattr('leapp.libraries.stdlib.api.produce', produce_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    expected = OSReleaseFacts(
        release_id='rhel',
        name='Red Hat Enterprise Linux Server',
        pretty_name='Red Hat Enterprise Linux',
        version='7.6 (Maipo)',
        version_id='7.6',
        variant='Server',
        variant_id='server')
    assert expected == get_os_release_info('tests/files/os-release')

    assert not get_os_release_info('tests/files/unexistent-file')
    assert reporting.create_report.called == 1
    assert 'inhibitor' in reporting.create_report.report_fields['flags']
