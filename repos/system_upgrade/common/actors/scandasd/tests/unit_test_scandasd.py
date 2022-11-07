import os

import pytest

from leapp.libraries.actor import scandasd
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.models import CopyFile, TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks


def test_dasd_exists(monkeypatch):
    monkeypatch.setattr(scandasd.api, 'current_actor', CurrentActorMocked(arch=architecture.ARCH_S390X))
    monkeypatch.setattr(scandasd.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(scandasd.api, 'produce', produce_mocked())
    monkeypatch.setattr(os.path, 'isfile', lambda dummy: True)
    scandasd.process()
    assert not scandasd.api.current_logger.infomsg
    assert scandasd.api.produce.called == 2
    tusut_flag = False
    uit_flag = False
    for msg in scandasd.api.produce.model_instances:
        if isinstance(msg, TargetUserSpaceUpgradeTasks):
            assert [CopyFile(src=scandasd.DASD_CONF)] == msg.copy_files
            assert msg.install_rpms == ['s390utils-core']
            tusut_flag = True
        elif isinstance(msg, UpgradeInitramfsTasks):
            assert [scandasd.DASD_CONF] == msg.include_files
            uit_flag = True
    assert tusut_flag and uit_flag


def test_dasd_not_found(monkeypatch):
    monkeypatch.setattr(scandasd.api, 'current_actor', CurrentActorMocked(arch=architecture.ARCH_S390X))
    monkeypatch.setattr(scandasd.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(os.path, 'isfile', lambda dummy: False)
    monkeypatch.setattr(scandasd.api, 'produce', produce_mocked())
    scandasd.process()
    assert scandasd.api.current_logger.infomsg
    assert scandasd.api.produce.called == 1
    assert len(scandasd.api.produce.model_instances) == 1
    assert isinstance(scandasd.api.produce.model_instances[0], TargetUserSpaceUpgradeTasks)
    assert scandasd.api.produce.model_instances[0].install_rpms == ['s390utils-core']
    assert not scandasd.api.produce.model_instances[0].copy_files


@pytest.mark.parametrize('isfile', [True, False])
@pytest.mark.parametrize('arch', [
    architecture.ARCH_X86_64,
    architecture.ARCH_ARM64,
    architecture.ARCH_PPC64LE,
])
def test_non_ibmz_arch(monkeypatch, isfile, arch):
    monkeypatch.setattr(scandasd.api, 'current_actor', CurrentActorMocked(arch=arch))
    monkeypatch.setattr(scandasd.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(scandasd.api, 'produce', produce_mocked())
    monkeypatch.setattr(os.path, 'isfile', lambda dummy: isfile)
    scandasd.process()
    assert not scandasd.api.current_logger.infomsg
    assert not scandasd.api.produce.called
