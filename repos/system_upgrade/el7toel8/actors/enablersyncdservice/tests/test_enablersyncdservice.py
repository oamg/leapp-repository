import pytest

from leapp.libraries.actor import enablersyncdservice
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import SystemdServiceFile, SystemdServicesInfoSource, SystemdServicesTasks


@pytest.mark.parametrize('service_file, should_produce', [
    (SystemdServiceFile(name='rsyncd.service', state='enabled'), True),
    (SystemdServiceFile(name='rsyncd.service', state='disabled'), False),
    (SystemdServiceFile(name='not-rsyncd.service', state='enabled'), False),
    (SystemdServiceFile(name='not-rsyncd.service', state='disabled'), False),
])
def test_task_produced(monkeypatch, service_file, should_produce):
    service_info = SystemdServicesInfoSource(service_files=[service_file])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[service_info]))
    monkeypatch.setattr(api, "produce", produce_mocked())

    enablersyncdservice.process()

    assert api.produce.called == should_produce
    if should_produce:
        assert api.produce.model_instances[0].to_enable == ['rsyncd.service']
