import pytest

from leapp import reporting
from leapp.libraries.actor import ziplcheckbootentries
from leapp.libraries.actor.ziplcheckbootentries import (
    extract_kernel_version,
    inhibit_if_entries_share_kernel_version,
    inhibit_if_invalid_zipl_configuration,
    inhibit_if_multiple_zipl_rescue_entries_present
)
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import BootEntry, SourceBootLoaderConfiguration
from leapp.snactor.fixture import current_actor_context
from leapp.utils.report import is_inhibitor


def test_inhibition_multiple_rescue_entries_present(monkeypatch):
    """Tests whether the upgrade process is inhibited when multiple rescue boot entries are present."""
    mocked_report = create_report_mocked()
    monkeypatch.setattr(architecture, 'matches_architecture', lambda dummy: True)
    monkeypatch.setattr(reporting, 'create_report', mocked_report)

    boot_entries = [
        BootEntry(title='entry_1', kernel_image="img"),
        BootEntry(title='entry_1_Rescue', kernel_image="img_Rescue"),
        BootEntry(title='entry_2', kernel_image="img"),
        BootEntry(title='entry_2_rescue-ver2.3', kernel_image="img_rescue"),
    ]

    inhibit_if_multiple_zipl_rescue_entries_present(SourceBootLoaderConfiguration(entries=boot_entries))

    assert mocked_report.called, 'Report should be created when multiple rescue entries are present.'

    fail_description = 'The correct rescue entries are not present in the report summary.'
    report_summary = mocked_report.report_fields['summary']
    for expected_rescue_entry in ['entry_1_Rescue', 'entry_2_rescue-ver2.3']:
        assert expected_rescue_entry in report_summary, fail_description

    fail_description = 'Upgrade should be inhibited on multiple rescue entries.'
    assert is_inhibitor(mocked_report.report_fields), fail_description


def test_inhibition_multiple_rescue_entries_not_present(monkeypatch):
    """Tests whether the upgrade process is not inhibited when multiple rescue boot entries are not present."""
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    boot_entries = [
        BootEntry(title='entry_1', kernel_image="img"),
        BootEntry(title='entry_2', kernel_image="img"),
        BootEntry(title='entry_2_rescue-ver2.3', kernel_image="img_rescue"),
    ]

    inhibit_if_multiple_zipl_rescue_entries_present(SourceBootLoaderConfiguration(entries=boot_entries))

    assert not reporting.create_report.called, 'Report was created, even if multiple rescue entries were not present.'


def test_inhibition_when_entries_do_not_share_kernel_image(monkeypatch):
    """Tests whether the IPU is not inhibited when there are no kernel images shared between boot entries."""
    entries = [
        BootEntry(title='Linux#0', kernel_image='/boot/vmlinuz-4.17.0-240.1.1.el8_3.x86_64'),
        BootEntry(title='Linux#1', kernel_image='/boot/vmlinuz-4.18.0-240.1.1.el8_3.x86_64')
    ]

    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    inhibit_if_entries_share_kernel_version(SourceBootLoaderConfiguration(entries=entries))
    assert not reporting.create_report.called


@pytest.mark.parametrize(
    ('boot_entries',),
    [([BootEntry(title='Linux0', kernel_image='/boot/vmlinuz-4.18.0-240.1.1.el8_3.x86_64'),
       BootEntry(title='Linux1', kernel_image='/boot/4.18.0-240.1.1.el8_3.x86_64')],),
     ([BootEntry(title='Linux0', kernel_image='/boot/vmlinuz-4.18.0-240.1.1.el8_3.x86_64'),
       BootEntry(title='Linux1', kernel_image='/boot/vmlinuz-4.18.0-240.1.1.el8_3.x86_64')],)])
def test_inhibit_when_entries_share_kernel_image(monkeypatch, boot_entries):
    """Tests whether the IPU gets inhibited when there are kernel images shared between boot entries."""

    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    inhibit_if_entries_share_kernel_version(SourceBootLoaderConfiguration(entries=boot_entries))

    assert reporting.create_report.called
    assert is_inhibitor(reporting.create_report.report_fields)

    report_summary = reporting.create_report.report_fields['summary']
    assert '- 4.18.0-240.1.1.el8_3.x86_64 (found in entries: "Linux0", "Linux1")' in report_summary


@pytest.mark.parametrize(
    ('boot_entries',),
    [([BootEntry(title='Linux', kernel_image='/boot/vmlinuz-4.18.0-240.1.1.el8_3.x86_64'),
       BootEntry(title='Linux-rescue', kernel_image='/boot/vmlinuz-rescue-4.18.0-240.1.1.el8_3.x86_64')],),
     ([BootEntry(title='Linux0-rescue', kernel_image='/boot/vmlinuz-rescue-4.18.0-240.1.1.el8_3.x86_64'),
       BootEntry(title='Linux1-rescue', kernel_image='/boot/vmlinuz-rescue-4.18.0-240.1.1.el8_3.x86_64')],)])
def test_inhibition_when_rescue_entries_share_kernel(monkeypatch, boot_entries):
    """
    Tests whether the IPU is not inhibited when there are kernel images with the same version shared between rescue
    boot entries.
    """
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    inhibit_if_entries_share_kernel_version(SourceBootLoaderConfiguration(entries=boot_entries))
    assert not reporting.create_report.called


@pytest.mark.parametrize(('arch',), [(arch,) for arch in architecture.ARCH_SUPPORTED])
def test_checks_performed_only_on_s390x_arch(arch, monkeypatch):
    """Tests whether the actor doesn't perform different architectures than s390x."""
    should_perform = False
    if arch == architecture.ARCH_S390X:  # Rescue entries should be checked only on s390x.
        should_perform = True

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=arch))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    boot_entries = [BootEntry(title='rescue0', kernel_image='/boot/vmlinuz-rescue-4.18.0-240.1.1.el8_3.x86_64'),
                    BootEntry(title='rescue1', kernel_image='/boot/vmlinuz-rescue-4.19.0-240.1.1.el8_3.x86_64')]

    inhibit_if_invalid_zipl_configuration(SourceBootLoaderConfiguration(entries=boot_entries))

    fail_description = 'Rescue entries should not be checked on non s390x architecture.'
    if should_perform:
        fail_description = 'No report was created when running on s390x and multiple rescue entries were used.'
    assert bool(reporting.create_report.called) == should_perform, fail_description

    if should_perform:
        inhibitor_description = 'contains multiple rescue boot entries'
        assert inhibitor_description in reporting.create_report.report_fields['summary']

    boot_entries = [BootEntry(title='Linux1', kernel_image='/boot/vmlinuz-4.18.0-240.1.1.el8_3.x86_64'),
                    BootEntry(title='Linux2', kernel_image='/boot/vmlinuz-4.18.0-240.1.1.el8_3.x86_64')]

    inhibit_if_invalid_zipl_configuration(SourceBootLoaderConfiguration(entries=boot_entries))

    fail_description = 'Check for boot entries with the same kernel version should not be performed on non s390x arch.'
    if should_perform:
        fail_description = ('No report was created when running on s390x and boot entries'
                            'with the same kernel version are present')
    assert bool(reporting.create_report.called) == should_perform, fail_description
    if should_perform:
        inhibitor_description = 'contains boot entries sharing the same kernel version'
        assert inhibitor_description in reporting.create_report.report_fields['summary']


def test_extract_kernel_version():
    # Manually generated via experimentation with the zipl-switch-to-blscfg
    versions_from_img_paths = [
        ('/boot/vmlinuz-4.18.0-240.1.1.el8_3.x86_64', '4.18.0-240.1.1.el8_3.x86_64'),
        ('/boot/4.18.0-240.1.1.el8_3.x86_64', '4.18.0-240.1.1.el8_3.x86_64'),
        ('/boot/patched-4.18.0-240.1.1.el8_3.x86_64', 'patched-4.18.0-240.1.1.el8_3.x86_64'),
        ('patched-4.18.0-240.1.1.el8_3.x86_64', 'patched-4.18.0-240.1.1.el8_3.x86_64'),
    ]

    for path, version in versions_from_img_paths:
        assert extract_kernel_version(path) == version
