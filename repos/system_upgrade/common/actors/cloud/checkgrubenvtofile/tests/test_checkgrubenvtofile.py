import pytest

from leapp import reporting
from leapp.libraries.actor import checkgrubenvtofile
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import FirmwareFacts, HybridImageAzure

BIOS_FIRMWARE = FirmwareFacts(firmware='bios')
EFI_FIRMWARE = FirmwareFacts(firmware='efi')


@pytest.mark.parametrize('is_hybrid', [True, False])
@pytest.mark.parametrize('is_bios', [True, False])
@pytest.mark.parametrize('is_symlink', [True, False])
def test_check_grubenv_to_file(monkeypatch, tmpdir, is_hybrid, is_bios, is_symlink):

    should_report = all([is_hybrid, is_bios, is_symlink])

    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    firmware = BIOS_FIRMWARE if is_bios else EFI_FIRMWARE
    msgs = [firmware] + ([HybridImageAzure(grubenv_is_symlink_to_efi=is_symlink)] if is_hybrid else [])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', msgs=msgs))
    monkeypatch.setattr(api, "produce", produce_mocked())

    checkgrubenvtofile.process()

    if should_report:
        assert reporting.create_report.called == 1
        assert 'hybrid' in reporting.create_report.report_fields['title']
        assert api.produce.called == 1
    else:
        assert reporting.create_report.called == 0
        assert api.produce.called == 0
