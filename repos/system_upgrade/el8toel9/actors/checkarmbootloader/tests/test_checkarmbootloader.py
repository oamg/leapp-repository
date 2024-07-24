import pytest

from leapp.libraries.actor import checkarmbootloader
from leapp.libraries.common.config.architecture import ARCH_ARM64, ARCH_SUPPORTED
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.libraries.stdlib import api


@pytest.mark.parametrize('arch', [arch for arch in ARCH_SUPPORTED if not arch == ARCH_ARM64])
def test_not_x86_64_passes(monkeypatch, arch):
    """
    Test no message is generated on an architecture different from ARM
    """

    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=arch))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkarmbootloader.process()

    assert 'Architecture not ARM.' in api.current_logger.infomsg[0]
    assert not api.produce.called


@pytest.mark.parametrize('target_version', ['9.2', '9.4'])
def test_valid_path(monkeypatch, target_version):
    """
    Test no message is generated on a supported path
    """

    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(
        api, 'current_actor',
        CurrentActorMocked(arch=ARCH_ARM64, src_ver='8.10', dst_ver=target_version)
    )

    checkarmbootloader.process()

    assert 'Upgrade on ARM architecture on a compatible path' in api.current_logger.infomsg[0]
    assert not api.produce.called


def test_invalid_path(monkeypatch):
    """
    Test message is generated on an invalid upgrade path
    """

    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(
        api, 'current_actor',
        CurrentActorMocked(arch=ARCH_ARM64, src_ver='8.10', dst_ver='9.5')
    )

    checkarmbootloader.process()

    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1

    msg = api.produce.model_instances[0]
    assert checkarmbootloader.ARM_GRUB_PACKAGE_NAME in msg.install_rpms
    assert checkarmbootloader.ARM_SHIM_PACKAGE_NAME in msg.install_rpms
