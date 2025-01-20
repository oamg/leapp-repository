import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import removeupgradebootentry
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import ArmWorkaroundEFIBootloaderInfo, BootContent, EFIBootEntry, FirmwareFacts


class run_mocked(object):
    def __init__(self):
        self.args = []

    def __call__(self, args, split=True):
        self.args.append(args)


@pytest.mark.parametrize('firmware', ['bios', 'efi'])
@pytest.mark.parametrize('arch', [architecture.ARCH_X86_64, architecture.ARCH_S390X])
@pytest.mark.parametrize('has_separate_bls_dir', [True, False])
def test_remove_boot_entry(firmware, arch, has_separate_bls_dir, monkeypatch):
    def get_upgrade_kernel_filepath_mocked():
        return '/abc'

    messages = [FirmwareFacts(firmware=firmware)]
    if has_separate_bls_dir:
        some_efi_entry = EFIBootEntry(boot_number='0001', label='entry', active=True, efi_bin_source='')
        workaround_info = ArmWorkaroundEFIBootloaderInfo(
            original_entry=some_efi_entry,
            upgrade_entry=some_efi_entry,
            upgrade_bls_dir='/boot/upgrade-loader/entries',
            upgrade_entry_efi_path='/boot/efi/EFI/leapp/'
        )
        messages.append(workaround_info)

    monkeypatch.setattr(removeupgradebootentry, 'get_upgrade_kernel_filepath', get_upgrade_kernel_filepath_mocked)
    monkeypatch.setattr(removeupgradebootentry, 'run', run_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch, msgs=messages))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    removeupgradebootentry.remove_boot_entry()

    boot_mounts = [['/bin/mount', '/boot']]
    if firmware == 'efi':
        boot_mounts.append(['/bin/mount', '/boot/efi'])

    calls = boot_mounts
    if not has_separate_bls_dir:
        # If we are using a separate BLS dir (ARM specific), then do not call anything
        calls += [['/usr/sbin/grubby', '--remove-kernel=/abc']]
        if arch == architecture.ARCH_S390X:
            calls.append(['/usr/sbin/zipl'])
        calls.append(['/bin/mount', '-a'])

    assert removeupgradebootentry.run.args == calls


def test_get_upgrade_kernel_filepath(monkeypatch):
    # BootContent message available
    def consume_message_mocked(*models):
        yield BootContent(kernel_path='/abc', initram_path='/def', kernel_hmac_path='/ghi')

    monkeypatch.setattr(api, 'consume', consume_message_mocked)

    kernel_path = removeupgradebootentry.get_upgrade_kernel_filepath()

    assert kernel_path == '/abc'

    # No BootContent message available
    def consume_no_message_mocked(*models):
        yield None

    monkeypatch.setattr(api, 'consume', consume_no_message_mocked)

    with pytest.raises(StopActorExecutionError):
        removeupgradebootentry.get_upgrade_kernel_filepath()
