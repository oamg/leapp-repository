import pytest

from leapp.libraries.actor import enabledeviceciofreeservice
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import SystemdServicesTasks


def test_task_produced_on_s390(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=architecture.ARCH_S390X))
    monkeypatch.setattr(api, "produce", produce_mocked())

    enabledeviceciofreeservice.process()

    assert api.produce.called
    assert isinstance(api.produce.model_instances[0], SystemdServicesTasks)
    assert api.produce.model_instances[0].to_enable == ['device_cio_free.service']


@pytest.mark.parametrize('arch', [
    architecture.ARCH_X86_64,
    architecture.ARCH_ARM64,
    architecture.ARCH_PPC64LE,
])
def test_task_not_produced_on_non_s390(monkeypatch, arch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=arch))
    monkeypatch.setattr(api, "produce", produce_mocked())

    enabledeviceciofreeservice.process()

    assert not api.produce.called
