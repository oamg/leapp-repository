import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries import stdlib
from leapp.libraries.actor import library
from leapp.models import BootContent


class call_mocked(object):
    def __call__(self, args, split=True):
        self.args = args


def test_add_boot_entry(monkeypatch):
    def get_boot_file_paths_mocked():
        return '/abc', '/def'
    monkeypatch.setattr(library, 'get_boot_file_paths', get_boot_file_paths_mocked)
    monkeypatch.setenv('LEAPP_DEBUG', '1')
    monkeypatch.setattr(stdlib, 'call', call_mocked())

    library.add_boot_entry()

    assert ' '.join(stdlib.call.args) == ('/usr/sbin/grubby --add-kernel=/abc --initrd=/def --title=RHEL'
                                          ' Upgrade Initramfs --copy-default --make-default --args="debug'
                                          ' enforcing=0 rd.plymouth=0 plymouth.enable=0"')


def test_get_boot_file_paths(monkeypatch):
    # BootContent message available
    def consume_message_mocked(*models):
        yield BootContent(kernel_path='/ghi', initram_path='/jkl')
    monkeypatch.setattr('leapp.libraries.stdlib.api.consume', consume_message_mocked)

    kernel_path, initram_path = library.get_boot_file_paths()

    assert kernel_path == '/ghi' and initram_path == '/jkl'

    # No BootContent message available
    def consume_no_message_mocked(*models):
        yield None
    monkeypatch.setattr('leapp.libraries.stdlib.api.consume', consume_no_message_mocked)

    with pytest.raises(StopActorExecutionError):
        library.get_boot_file_paths()
