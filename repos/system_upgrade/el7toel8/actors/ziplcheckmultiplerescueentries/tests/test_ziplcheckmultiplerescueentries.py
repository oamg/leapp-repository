import pytest

from leapp import reporting
from leapp.libraries.actor import ziplcheckmultiplerescueentries
from leapp.libraries.actor.ziplcheckmultiplerescueentries import inhibit_if_multiple_zipl_rescue_entries_present
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import BootEntry, SourceBootLoaderConfiguration
from leapp.snactor.fixture import current_actor_context


def test_inhibition_multiple_rescue_entries_present(monkeypatch):
    """Tests whether the upgrade process is inhibited when multiple rescue boot entries are present."""
    mocked_report = create_report_mocked()
    monkeypatch.setattr(architecture, 'matches_architecture', lambda dummy: True)
    monkeypatch.setattr(reporting, 'create_report', mocked_report)

    boot_entries = [
        BootEntry(title='entry_1'),
        BootEntry(title='entry_1_Rescue'),
        BootEntry(title='entry_2'),
        BootEntry(title='entry_2_rescue-ver2.3'),  # Typically is the `rescue` substring surrounded
    ]

    inhibit_if_multiple_zipl_rescue_entries_present(SourceBootLoaderConfiguration(entries=boot_entries))

    assert mocked_report.called, 'Report should be created when multiple rescue entries are present.'

    fail_description = 'The correct rescue entries are not present in the report summary.'
    report_summary = mocked_report.report_fields['summary']
    for expected_rescue_entry in ['entry_1_Rescue', 'entry_2_rescue-ver2.3']:
        assert expected_rescue_entry in report_summary, fail_description

    fail_description = 'Upgrade should be inhibited on multiple rescue entries.'
    assert 'inhibitor' in mocked_report.report_fields['flags'], fail_description


def test_inhibition_multiple_rescue_entries_not_present(monkeypatch):
    """Tests whether the upgrade process is not inhibited when multiple rescue boot entries are not present."""
    monkeypatch.setattr(architecture, 'matches_architecture', lambda dummy: True)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    boot_entries = [
        BootEntry(title='entry_1'),
        BootEntry(title='entry_2'),
        BootEntry(title='entry_2_rescue-ver2.3'),
    ]

    inhibit_if_multiple_zipl_rescue_entries_present(SourceBootLoaderConfiguration(entries=boot_entries))

    assert not reporting.create_report.called, 'Report was created, even if multiple rescue entries were not present.'


@pytest.mark.parametrize(
    ('arch',),
    [(arch,) for arch in architecture.ARCH_SUPPORTED]
)
def test_checks_performed_only_on_s390x_arch(arch, monkeypatch):
    """Tests whether the actor doesn't perform different architectures than s390x."""

    should_perform = False
    if arch == architecture.ARCH_S390X:  # Rescue entries should be checked only on s390x.
        should_perform = True

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=arch))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    boot_entries = [BootEntry(title='rescue0'), BootEntry(title='rescue1')]
    inhibit_if_multiple_zipl_rescue_entries_present(SourceBootLoaderConfiguration(entries=boot_entries))

    fail_description = 'Rescue entries should not be checked on non s390x architecture.'
    if should_perform:
        fail_description = 'No report was created when running on s390x and multiple rescue entries were used.'
    assert bool(reporting.create_report.called) == should_perform, fail_description
