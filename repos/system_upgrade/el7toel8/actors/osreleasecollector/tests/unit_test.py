from leapp.libraries.actor.library import get_os_release_model
from leapp.libraries.common import requirearchver
from leapp.libraries.common.testutils import produce_mocked, report_generic_mocked
from leapp.models import OSReleaseFacts


def test_get_os_release_model(monkeypatch):
    input_data = {
        'ID': 'rhel',
        'NAME': 'Red Hat Enterprise Linux Server',
        'PRETTY_NAME': 'Red Hat Enterprise Linux',
        'VARIANT': 'Server',
        'VARIANT_ID': 'server',
        'VERSION': '7.6 (Maipo)',
        'VERSION_ID': '7.6'
    }
    expected = OSReleaseFacts(
        release_id='rhel',
        name='Red Hat Enterprise Linux Server',
        pretty_name='Red Hat Enterprise Linux',
        version='7.6 (Maipo)',
        version_id='7.6',
        variant='Server',
        variant_id='server'
    )

    monkeypatch.setattr(requirearchver, 'get_os_release_info', lambda _unused: input_data)
    assert expected == get_os_release_model('unused_in_test')
