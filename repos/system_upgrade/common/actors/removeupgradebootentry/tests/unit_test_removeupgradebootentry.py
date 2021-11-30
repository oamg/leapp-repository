import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import removeupgradebootentry
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import BootContent, FirmwareFacts


class run_mocked(object):
    args = []

    def __call__(self, args, split=True):
        self.args.append(args)


@pytest.mark.parametrize('firmware', ['bios', 'efi'])
@pytest.mark.parametrize('arch', [architecture.ARCH_X86_64, architecture.ARCH_S390X])
def test_remove_boot_entry(firmware, arch, monkeypatch):
    def get_upgrade_kernel_filepath_mocked():
        return '/abc'

    def consume_systemfacts_mocked(*models):
        yield FirmwareFacts(firmware=firmware)

    monkeypatch.setattr(removeupgradebootentry, 'get_upgrade_kernel_filepath', get_upgrade_kernel_filepath_mocked, )
    monkeypatch.setattr(api, 'consume', consume_systemfacts_mocked)
    monkeypatch.setattr(removeupgradebootentry, 'run', run_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    removeupgradebootentry.remove_boot_entry()

    boot_mounts = [['/bin/mount', '/boot']]
    if firmware == 'efi':
        boot_mounts.append(['/bin/mount', '/boot/efi'])

    calls = boot_mounts + [['/usr/sbin/grubby', '--remove-kernel=/abc']]
    if arch == architecture.ARCH_S390X:
        calls.append(['/usr/sbin/zipl'])
    calls.append(['/bin/mount', '-a'])

    assert removeupgradebootentry.run.args == calls

    # clear args for next run
    del removeupgradebootentry.run.args[:]


def test_get_upgrade_kernel_filepath(monkeypatch):
    # BootContent message available
    def consume_message_mocked(*models):
        yield BootContent(kernel_path='/abc', initram_path='/def')

    monkeypatch.setattr(api, 'consume', consume_message_mocked)

    kernel_path = removeupgradebootentry.get_upgrade_kernel_filepath()

    assert kernel_path == '/abc'

    # No BootContent message available
    def consume_no_message_mocked(*models):
        yield None

    monkeypatch.setattr(api, 'consume', consume_no_message_mocked)

    with pytest.raises(StopActorExecutionError):
        removeupgradebootentry.get_upgrade_kernel_filepath()
