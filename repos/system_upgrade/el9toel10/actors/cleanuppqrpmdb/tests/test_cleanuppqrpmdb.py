import os

import pytest

from leapp.libraries.actor import cleanuppqrpmdb
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api


@pytest.mark.parametrize('src_ver', ['9.9', '9.10', '9.11'])
def test_removes_db_on_matching_version(monkeypatch, src_ver):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver=src_ver, dst_ver='10.0'))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(os.path, 'isdir', lambda path: True)

    removed = []
    monkeypatch.setattr(cleanuppqrpmdb.shutil, 'rmtree', removed.append)

    cleanuppqrpmdb.process()

    assert removed == [cleanuppqrpmdb.PQRPM_DB_DIR]


@pytest.mark.parametrize('src_ver', ['9.8', '9.6'])
def test_skips_on_old_version(monkeypatch, src_ver):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver=src_ver, dst_ver='10.0'))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    # isdir/rmtree would raise if called, since they are not mocked here.
    removed = []
    monkeypatch.setattr(cleanuppqrpmdb.shutil, 'rmtree', removed.append)

    cleanuppqrpmdb.process()

    assert not removed


def test_skips_when_dir_missing(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='9.9', dst_ver='10.0'))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(os.path, 'isdir', lambda path: False)

    removed = []
    monkeypatch.setattr(cleanuppqrpmdb.shutil, 'rmtree', removed.append)

    cleanuppqrpmdb.process()

    assert not removed


def test_logs_warning_on_failure(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='9.9', dst_ver='10.0'))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(os.path, 'isdir', lambda path: True)

    def _raise(path):
        raise OSError('permission denied')

    monkeypatch.setattr(cleanuppqrpmdb.shutil, 'rmtree', _raise)

    cleanuppqrpmdb.process()

    assert any('Failed to remove' in str(msg) for msg in api.current_logger.warnmsg)
