import pytest

from leapp.libraries.stdlib import api
from leapp.libraries.actor import library


class remove_file_mocked(object):
    def __init__(self):
        self.file = ''

    def __call__(self, file):
        self.file = file


class logger_mocked(object):
    def __init__(self):
        self.infomsg = ''
        self.errmsg = ''

    def info(self, msg):
        self.infomsg = msg

    def error(self, msg):
        self.errmsg = msg

    def __call__(self):
        return self


def test_remove_log_exists(monkeypatch):
    def file_exists(filepath):
        return True
    monkeypatch.setattr('os.path.isfile', file_exists)
    monkeypatch.setattr(library, 'remove_file', remove_file_mocked())
    monkeypatch.setattr('leapp.libraries.stdlib.api.current_logger', logger_mocked())

    library.remove_log()

    assert library.remove_file.file == '/var/log/upgrade.log'
    assert "already exists a log" in api.current_logger.infomsg


def test_remove_log_no_exists(monkeypatch):
    def file_no_exists(filepath):
        return False
    monkeypatch.setattr('os.path.isfile', file_no_exists)
    monkeypatch.setattr(library, 'remove_file', remove_file_mocked())
    monkeypatch.setattr('leapp.libraries.stdlib.api.current_logger', logger_mocked())

    library.remove_log()

    assert not library.remove_file.file
    assert not api.current_logger.infomsg


def test_remove_file_that_does_not_exist(monkeypatch):
    def remove_mocked(filepath):
        raise OSError
    monkeypatch.setattr('os.remove', remove_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    library.remove_file('/filepath')

    assert "Could not remove /filepath" in api.current_logger.errmsg
