import pytest

from leapp.libraries import stdlib
from leapp.libraries.actor import sourcebootloaderscanner
from leapp.libraries.common.testutils import produce_mocked

GRUBBY_INFO_ALL_STDOUT = '''index=0
kernel="/boot/vmlinuz-4.18.0-305.7.1.el8_4.x86_64"
args="ro uned_params"
root="/someroot"
initrd="/boot/initramfs-4.18.0-305.7.1.el8_4.x86_64.img"
title="Linux"
id="some_id"
index=1
kernel="/boot/vmlinuz-4.18.0-305.3.1.el8_4.x86_64"
args="ro"
root="/someroot"
initrd="/boot/initramfs-4.18.0-305.3.1.el8_4.x86_64.img"
title="Linux old-kernel"
id="some_id2"
index=2
non linux entry'''


def test_scan_boot_entries(monkeypatch):
    """Tests whether the library correctly identifies boot entries in the grubby output."""
    def run_mocked(cmd, **kwargs):
        if cmd == ['grubby', '--info', 'ALL']:
            return {
                'stdout': GRUBBY_INFO_ALL_STDOUT.split('\n')
            }
        raise ValueError('Tried to run unexpected command.')

    actor_produces = produce_mocked()

    # The library imports `run` all the way (from ... import run), therefore,
    # we must monkeypatch the reference directly in the actor's library namespace
    monkeypatch.setattr(sourcebootloaderscanner, 'run', run_mocked)
    monkeypatch.setattr(stdlib.api, 'produce', actor_produces)

    sourcebootloaderscanner.scan_source_boot_loader_configuration()

    fail_description = 'Only one SourceBootLoaderConfiguration message should be produced.'
    assert len(actor_produces.model_instances) == 1, fail_description

    bootloader_config = actor_produces.model_instances[0]

    fail_description = 'Found different number of boot entries than present in provided mocks.'
    assert len(bootloader_config.entries) == 2, fail_description

    expected_entries = [
        {'title': 'Linux', 'kernel_image': '/boot/vmlinuz-4.18.0-305.7.1.el8_4.x86_64'},
        {'title': 'Linux old-kernel', 'kernel_image': '/boot/vmlinuz-4.18.0-305.3.1.el8_4.x86_64'},
    ]

    actual_entries = sorted(bootloader_config.entries, key=lambda entry: entry.title)

    for actual_entry, expected_entry in zip(actual_entries, expected_entries):
        assert actual_entry.title == expected_entry['title']
        assert actual_entry.kernel_image == expected_entry['kernel_image']
