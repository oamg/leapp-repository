import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries import stdlib
from leapp.libraries.actor import library
from leapp.models import BootContent


class call_mocked(object):
    args = []

    def __call__(self, args, split=True):
        self.args.append(args)


def test_remove_boot_entry(monkeypatch):
    def get_upgrade_kernel_filepath_mocked():
        return '/abc'
    monkeypatch.setattr(library, 'get_upgrade_kernel_filepath', get_upgrade_kernel_filepath_mocked)
    monkeypatch.setattr(library, 'call', call_mocked())

    library.remove_boot_entry()

    assert library.call.args == [['/usr/sbin/grubby', '--remove-kernel=/abc'], ['/bin/mount', '-a']]


def test_get_upgrade_kernel_filepath(monkeypatch):
    # BootContent message available
    def consume_message_mocked(*models):
        yield BootContent(kernel_path='/abc', initram_path='/def')
    monkeypatch.setattr('leapp.libraries.stdlib.api.consume', consume_message_mocked)

    kernel_path = library.get_upgrade_kernel_filepath()

    assert kernel_path == '/abc'

    # No BootContent message available
    def consume_no_message_mocked(*models):
        yield None
    monkeypatch.setattr('leapp.libraries.stdlib.api.consume', consume_no_message_mocked)

    with pytest.raises(StopActorExecutionError):
        library.get_upgrade_kernel_filepath()
