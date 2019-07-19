import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.libraries.actor import library
from leapp.models import BootContent, FirmwareFacts


class run_mocked(object):
    args = []

    def __call__(self, args, split=True):
        self.args.append(args)


@pytest.mark.parametrize('firmware', ['bios', 'efi'])
def test_remove_boot_entry(firmware, monkeypatch):
    def get_upgrade_kernel_filepath_mocked():
        return '/abc'

    def consume_systemfacts_mocked(*models):
        yield FirmwareFacts(firmware=firmware)

    monkeypatch.setattr(library, 'get_upgrade_kernel_filepath', get_upgrade_kernel_filepath_mocked)
    monkeypatch.setattr(api, 'consume', consume_systemfacts_mocked)
    monkeypatch.setattr(library, 'run', run_mocked())

    library.remove_boot_entry()

    boot_mounts = [['/bin/mount', '/boot']]
    if firmware == 'efi':
        boot_mounts.append(['/bin/mount', '/boot/efi'])

    calls = boot_mounts + [['/usr/sbin/grubby', '--remove-kernel=/abc'], ['/bin/mount', '-a']]

    assert library.run.args == calls

    # clear args for next run
    del library.run.args[:]


def test_get_upgrade_kernel_filepath(monkeypatch):
    # BootContent message available
    def consume_message_mocked(*models):
        yield BootContent(kernel_path='/abc', initram_path='/def')
    monkeypatch.setattr(api, 'consume', consume_message_mocked)

    kernel_path = library.get_upgrade_kernel_filepath()

    assert kernel_path == '/abc'

    # No BootContent message available
    def consume_no_message_mocked(*models):
        yield None
    monkeypatch.setattr(api, 'consume', consume_no_message_mocked)

    with pytest.raises(StopActorExecutionError):
        library.get_upgrade_kernel_filepath()
