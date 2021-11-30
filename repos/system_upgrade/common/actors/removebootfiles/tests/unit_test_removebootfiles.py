import pytest

from leapp.exceptions import StopActorExecution
from leapp.libraries.actor import removebootfiles
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import BootContent


class remove_file_mocked(object):
    def __init__(self):
        self.called = 0
        self.files_to_remove = []

    def __call__(self, filename):
        self.called += 1
        self.files_to_remove.append(filename)


def test_remove_boot_files(monkeypatch):
    # BootContent message available
    def consume_message_mocked(*models):
        yield BootContent(kernel_path='/abc', initram_path='/def')

    monkeypatch.setattr('leapp.libraries.stdlib.api.consume', consume_message_mocked)
    monkeypatch.setattr(removebootfiles, 'remove_file', remove_file_mocked())

    removebootfiles.remove_boot_files()

    assert removebootfiles.remove_file.files_to_remove == ['/abc', '/def']

    # No BootContent message available
    def consume_no_message_mocked(*models):
        yield None

    monkeypatch.setattr('leapp.libraries.stdlib.api.consume', consume_no_message_mocked)
    monkeypatch.setattr(removebootfiles, 'remove_file', remove_file_mocked())
    monkeypatch.setattr('leapp.libraries.stdlib.api.current_logger', logger_mocked())

    with pytest.raises(StopActorExecution):
        removebootfiles.remove_boot_files()

    assert removebootfiles.remove_file.called == 0
    assert any("Did not receive a message" in msg for msg in api.current_logger.warnmsg)


def test_remove_file_that_does_not_exist(monkeypatch):
    def remove_mocked(filepath):
        raise OSError

    monkeypatch.setattr('os.remove', remove_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    removebootfiles.remove_file('/filepath')

    assert any("Could not remove /filepath" in msg for msg in api.current_logger.errmsg)
