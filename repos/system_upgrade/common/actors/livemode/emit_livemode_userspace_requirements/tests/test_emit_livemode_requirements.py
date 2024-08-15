import pytest

from leapp.libraries.actor import emit_livemode_userspace_requirements as emit_livemode_userspace_requirements_lib
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import LiveModeConfig, TargetUserSpaceUpgradeTasks


@pytest.mark.parametrize('livemode_config', (None, LiveModeConfig(squashfs_fullpath='<squashfs>', is_enabled=False)))
def test_no_emit_if_livemode_disabled(monkeypatch, livemode_config):
    messages = [livemode_config] if livemode_config else []
    actor_mock = CurrentActorMocked(msgs=messages)
    monkeypatch.setattr(api, 'current_actor', actor_mock)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    emit_livemode_userspace_requirements_lib.emit_livemode_userspace_requirements()

    assert not api.produce.called


def test_emit(monkeypatch):
    config = LiveModeConfig(squashfs_fullpath='<squashfs_path>', is_enabled=True, additional_packages=['EXTRA_PKG'])
    actor_mock = CurrentActorMocked(msgs=[config])
    monkeypatch.setattr(api, 'current_actor', actor_mock)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    emit_livemode_userspace_requirements_lib.emit_livemode_userspace_requirements()

    assert api.produce.called
    assert len(api.produce.model_instances) == 1

    required_pkgs = api.produce.model_instances[0]
    assert isinstance(required_pkgs, TargetUserSpaceUpgradeTasks)

    assert 'dracut-live' in required_pkgs.install_rpms
    assert 'dracut-squash' in required_pkgs.install_rpms
    assert 'EXTRA_PKG' in required_pkgs.install_rpms
