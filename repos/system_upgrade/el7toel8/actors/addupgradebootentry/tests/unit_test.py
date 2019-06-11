import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import library
from leapp.models import BootContent


class run_mocked(object):
    def __init__(self):
        self.args = None

    def __call__(self, args, split=False):
        self.args = args


class write_to_file_mocked(object):
    def __init__(self):
        self.content = None

    def __call__(self, filename, content):
        self.content = content


def test_add_boot_entry(monkeypatch):
    def get_boot_file_paths_mocked():
        return '/abc', '/def'
    monkeypatch.setattr(library, 'get_boot_file_paths', get_boot_file_paths_mocked)
    monkeypatch.setenv('LEAPP_DEBUG', '1')
    monkeypatch.setattr(library, 'run', run_mocked())

    library.add_boot_entry()

    assert library.run.args == ['/usr/sbin/grubby',
                                '--add-kernel', '/abc',
                                '--initrd', '/def',
                                '--title', 'RHEL Upgrade Initramfs',
                                '--copy-default',
                                '--make-default',
                                '--args',
                                'debug enforcing=0 rd.plymouth=0 plymouth.enable=0']


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


def test_fix_grub_config_error(monkeypatch):
    monkeypatch.setattr(library, 'write_to_file', write_to_file_mocked())
    library.fix_grub_config_error('files/grub_test.wrong')

    with open('files/grub_test.fixed') as f:
        assert library.write_to_file.content == f.read()
