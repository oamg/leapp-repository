import pytest

from leapp.exceptions import StopActorExecution
from leapp.libraries.stdlib import api
from leapp.libraries.actor import library
from leapp.models import BootContent


class remove_file_mocked(object):
    def __init__(self):
        self.called = 0
        self.files_to_remove = []

    def __call__(self, file):
        self.called += 1
        self.files_to_remove.append(file)


class logger_mocked(object):
    def warning(self, msg):
        self.warnmsg = msg

    def error(self, msg):
        self.errmsg = msg

    def __call__(self):
        return self


def test_remove_boot_files(monkeypatch):
    # BootContent message available
    def consume_message_mocked(*models):
        yield BootContent(kernel_path='/abc', initram_path='/def')
    monkeypatch.setattr('leapp.libraries.stdlib.api.consume', consume_message_mocked)
    monkeypatch.setattr(library, 'remove_file', remove_file_mocked())

    library.remove_boot_files()

    assert library.remove_file.files_to_remove == ['/abc', '/def']

    # No BootContent message available
    def consume_no_message_mocked(*models):
        yield None
    monkeypatch.setattr('leapp.libraries.stdlib.api.consume', consume_no_message_mocked)
    monkeypatch.setattr(library, 'remove_file', remove_file_mocked())
    monkeypatch.setattr('leapp.libraries.stdlib.api.current_logger', logger_mocked())

    with pytest.raises(StopActorExecution):
        library.remove_boot_files()

    assert library.remove_file.called == 0
    assert "Did not receive a message" in api.current_logger.warnmsg


def test_remove_file_that_does_not_exist(monkeypatch):
    def remove_mocked(filepath):
        raise OSError
    monkeypatch.setattr('os.remove', remove_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    library.remove_file('/filepath')

    assert "Could not remove /filepath" in api.current_logger.errmsg
