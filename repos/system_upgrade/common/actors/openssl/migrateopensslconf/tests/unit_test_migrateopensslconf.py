import os

import pytest

from leapp.libraries.actor import migrateopensslconf
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import CalledProcessError


class PathExistsMocked(object):
    def __init__(self, existing_files=None):
        self.called = 0
        self._existing_files = existing_files if existing_files else []

    def __call__(self, fpath):
        self.called += 1
        return fpath in self._existing_files


class IsOpensslModifiedMocked(object):
    def __init__(self, ret_values):
        self._ret_values = ret_values
        # ret_values is list of bools to return on each call. ret_values.pop(0)
        # if the list becomes empty, returns False

        self.called = 0

    def __call__(self):
        self.called += 1
        if not self._ret_values:
            return False
        return self._ret_values.pop(0)


class SafeMVFileMocked(object):
    def __init__(self, ret_values):
        self._ret_values = ret_values
        # ret_values is list of bools to return on each call. ret_values.pop(0)
        # if the list becomes empty, returns False

        self.called = 0
        self.args_list = []

    def __call__(self, src, dst):
        self.called += 1
        self.args_list.append((src, dst))
        if not self._ret_values:
            return False
        return self._ret_values.pop(0)


def test_migrate_openssl_nothing_to_do(monkeypatch):
    monkeypatch.setattr(migrateopensslconf.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(migrateopensslconf, '_is_openssl_modified', IsOpensslModifiedMocked([False]))
    monkeypatch.setattr(migrateopensslconf, '_safe_mv_file', SafeMVFileMocked([False]))
    monkeypatch.setattr(os.path, 'exists', PathExistsMocked())

    migrateopensslconf.process()
    assert not os.path.exists.called
    assert not migrateopensslconf._safe_mv_file.called

    monkeypatch.setattr(migrateopensslconf, '_is_openssl_modified', IsOpensslModifiedMocked([True]))
    migrateopensslconf.process()
    assert os.path.exists.called
    assert migrateopensslconf.api.current_logger.dbgmsg
    assert not migrateopensslconf._safe_mv_file.called


def test_migrate_openssl_failed_backup(monkeypatch):
    monkeypatch.setattr(migrateopensslconf.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(migrateopensslconf, '_is_openssl_modified', IsOpensslModifiedMocked([True]))
    monkeypatch.setattr(migrateopensslconf, '_safe_mv_file', SafeMVFileMocked([False]))
    monkeypatch.setattr(os.path, 'exists', PathExistsMocked([migrateopensslconf.OPENSSL_CONF_RPMNEW]))

    migrateopensslconf.process()
    assert migrateopensslconf._safe_mv_file.called == 1
    assert migrateopensslconf._safe_mv_file.args_list[0][0] == migrateopensslconf.DEFAULT_OPENSSL_CONF
    assert migrateopensslconf.api.current_logger.errmsg


def test_migrate_openssl_ok(monkeypatch):
    monkeypatch.setattr(migrateopensslconf.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(migrateopensslconf, '_is_openssl_modified', IsOpensslModifiedMocked([True]))
    monkeypatch.setattr(migrateopensslconf, '_safe_mv_file', SafeMVFileMocked([True, True]))
    monkeypatch.setattr(os.path, 'exists', PathExistsMocked([migrateopensslconf.OPENSSL_CONF_RPMNEW]))

    migrateopensslconf.process()
    assert migrateopensslconf._safe_mv_file.called == 2
    assert migrateopensslconf._safe_mv_file.args_list[1][1] == migrateopensslconf.DEFAULT_OPENSSL_CONF
    assert not migrateopensslconf.api.current_logger.errmsg


def test_migrate_openssl_failed_migrate(monkeypatch):
    monkeypatch.setattr(migrateopensslconf.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(migrateopensslconf, '_is_openssl_modified', IsOpensslModifiedMocked([True]))
    monkeypatch.setattr(migrateopensslconf, '_safe_mv_file', SafeMVFileMocked([True, False, True]))
    monkeypatch.setattr(os.path, 'exists', PathExistsMocked([migrateopensslconf.OPENSSL_CONF_RPMNEW]))

    migrateopensslconf.process()
    assert migrateopensslconf._safe_mv_file.called == 3
    assert migrateopensslconf._safe_mv_file.args_list[2][1] == migrateopensslconf.DEFAULT_OPENSSL_CONF
    assert migrateopensslconf.api.current_logger.errmsg


def test_migrate_openssl_failed_restore(monkeypatch):
    monkeypatch.setattr(migrateopensslconf.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(migrateopensslconf, '_is_openssl_modified', IsOpensslModifiedMocked([True]))
    monkeypatch.setattr(migrateopensslconf, '_safe_mv_file', SafeMVFileMocked([True]))
    monkeypatch.setattr(os.path, 'exists', PathExistsMocked([migrateopensslconf.OPENSSL_CONF_RPMNEW]))

    migrateopensslconf.process()
    assert migrateopensslconf._safe_mv_file.called == 3
    assert len(migrateopensslconf.api.current_logger.errmsg) == 2


class MockedRun(object):
    def __init__(self, raise_err):
        self.called = 0
        self.args = None
        self._raise_err = raise_err

    def __call__(self, args):
        self.called += 1
        self.args = args
        if self._raise_err:
            raise CalledProcessError(
                message='A Leapp Command Error occurred.',
                command=args,
                result={'signal': None, 'exist_code': 1, 'pid': 0, 'stdout': 'fale', 'stderr': 'fake'}
            )
        # NOTE(pstodulk) ignore return as the code in the library does not use it


@pytest.mark.parametrize('result', (True, False))
def test_is_openssl_modified(monkeypatch, result):
    monkeypatch.setattr(migrateopensslconf, 'run', MockedRun(result))
    assert migrateopensslconf._is_openssl_modified() is result
    assert migrateopensslconf.run.called == 1


@pytest.mark.parametrize('result', (True, False))
def test_safe_mv_file(monkeypatch, result):
    monkeypatch.setattr(migrateopensslconf, 'run', MockedRun(not result))
    assert migrateopensslconf._safe_mv_file('foo', 'bar') is result
    assert ['mv', 'foo', 'bar'] == migrateopensslconf.run.args
