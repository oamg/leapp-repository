import os

import pytest

from leapp.libraries.actor import scanzfcp
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.models import CopyFile, TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks


def test_zfcp_exists(monkeypatch):
    monkeypatch.setattr(scanzfcp.api, 'current_actor', CurrentActorMocked(arch=architecture.ARCH_S390X))
    monkeypatch.setattr(scanzfcp.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(scanzfcp.api, 'produce', produce_mocked())
    monkeypatch.setattr(os.path, 'isfile', lambda dummy: True)
    scanzfcp.process()
    assert not scanzfcp.api.current_logger.infomsg
    assert scanzfcp.api.produce.called == 2
    tusut_flag = False
    uit_flag = False
    for msg in scanzfcp.api.produce.model_instances:
        if isinstance(msg, TargetUserSpaceUpgradeTasks):
            assert [CopyFile(src=scanzfcp.ZFCP_CONF)] == msg.copy_files
            assert msg.install_rpms == ['s390utils-core']
            tusut_flag = True
        elif isinstance(msg, UpgradeInitramfsTasks):
            assert [scanzfcp.ZFCP_CONF] == msg.include_files
            uit_flag = True
    assert tusut_flag and uit_flag


def test_zfcp_not_found(monkeypatch):
    monkeypatch.setattr(scanzfcp.api, 'current_actor', CurrentActorMocked(arch=architecture.ARCH_S390X))
    monkeypatch.setattr(scanzfcp.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(scanzfcp.os.path, 'isfile', lambda dummy: False)
    monkeypatch.setattr(scanzfcp.api, 'produce', produce_mocked())
    scanzfcp.process()
    assert scanzfcp.api.current_logger.infomsg
    assert scanzfcp.api.produce.called == 1
    assert len(scanzfcp.api.produce.model_instances) == 1
    assert isinstance(scanzfcp.api.produce.model_instances[0], TargetUserSpaceUpgradeTasks)
    assert scanzfcp.api.produce.model_instances[0].install_rpms == ['s390utils-core']
    assert not scanzfcp.api.produce.model_instances[0].copy_files


@pytest.mark.parametrize('isfile', [True, False])
@pytest.mark.parametrize('arch', [
    architecture.ARCH_X86_64,
    architecture.ARCH_ARM64,
    architecture.ARCH_PPC64LE,
])
def test_non_ibmz_arch(monkeypatch, isfile, arch):
    monkeypatch.setattr(scanzfcp.api, 'current_actor', CurrentActorMocked(arch=arch))
    monkeypatch.setattr(scanzfcp.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(scanzfcp.api, 'produce', produce_mocked())
    monkeypatch.setattr(os.path, 'isfile', lambda dummy: isfile)
    scanzfcp.process()
    assert not scanzfcp.api.current_logger.infomsg
    assert not scanzfcp.api.produce.called
