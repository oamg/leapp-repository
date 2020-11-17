import os

import pytest

from leapp.libraries.actor import scandasd
from leapp.libraries.common.config.architecture import ARCH_S390X
from leapp.libraries.common.testutils import logger_mocked, produce_mocked
from leapp.models import CopyFile, TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks


def test_dasd_exists(monkeypatch):
    monkeypatch.setattr(scandasd.architecture, 'matches_architecture', lambda dummy: True)
    monkeypatch.setattr(scandasd.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(scandasd.api, 'produce', produce_mocked())
    monkeypatch.setattr(os.path, 'isfile', lambda dummy: True)
    scandasd.process()
    assert not scandasd.api.current_logger.warnmsg
    assert scandasd.api.produce.called == 2
    tusut_flag = False
    uit_flag = False
    for msg in scandasd.api.produce.model_instances:
        if isinstance(msg, TargetUserSpaceUpgradeTasks):
            assert [CopyFile(src=scandasd.DASD_CONF)] == msg.copy_files
            tusut_flag = True
        elif isinstance(msg, UpgradeInitramfsTasks):
            assert [scandasd.DASD_CONF] == msg.include_files
            uit_flag = True
    assert tusut_flag and uit_flag


def test_dasd_not_found(monkeypatch):
    monkeypatch.setattr(scandasd.architecture, 'matches_architecture', lambda dummy: True)
    monkeypatch.setattr(scandasd.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(os.path, 'isfile', lambda dummy: False)
    monkeypatch.setattr(scandasd.api, 'produce', produce_mocked())
    scandasd.process()
    assert scandasd.api.current_logger.warnmsg
    assert not scandasd.api.produce.called


@pytest.mark.parametrize('isfile', [True, False])
def test_non_ibmz_arch(monkeypatch, isfile):
    monkeypatch.setattr(scandasd.architecture, 'matches_architecture', lambda dummy: False)
    monkeypatch.setattr(scandasd.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(scandasd.api, 'produce', produce_mocked())
    monkeypatch.setattr(os.path, 'isfile', lambda dummy: isfile)
    scandasd.process()
    assert not scandasd.api.current_logger.warnmsg
    assert not scandasd.api.produce.called
