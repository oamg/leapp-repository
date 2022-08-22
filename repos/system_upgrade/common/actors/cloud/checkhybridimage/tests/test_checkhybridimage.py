import pytest

from leapp import reporting
from leapp.libraries.actor import checkhybridimage
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import FirmwareFacts, InstalledRPM, RPM
from leapp.reporting import Report

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'
WA_AGENT_RPM = RPM(
    name='WALinuxAgent', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
    pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'
)
NO_AGENT_RPM = RPM(
    name='NoAgent', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
    pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'
)

INSTALLED_AGENT = InstalledRPM(items=[WA_AGENT_RPM])
NOT_INSTALLED_AGENT = InstalledRPM(items=[NO_AGENT_RPM])

BIOS_FIRMWARE = FirmwareFacts(firmware='bios')
EFI_FIRMWARE = FirmwareFacts(firmware='efi')

BIOS_PATH = '/boot/grub2/grubenv'
EFI_PATH = '/boot/efi/EFI/redhat/grubenv'


def test_hybrid_image(monkeypatch, tmpdir):
    grubenv_efi = tmpdir.join('grubenv_efi')
    grubenv_efi.write('grubenv')

    grubenv_boot = tmpdir.join('grubenv_boot')
    grubenv_boot.mksymlinkto('grubenv_efi')

    monkeypatch.setattr(checkhybridimage, 'BIOS_PATH', grubenv_boot.strpath)
    monkeypatch.setattr(checkhybridimage, 'EFI_PATH', grubenv_efi.strpath)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(
        api, 'current_actor', CurrentActorMocked(arch='x86_64', msgs=[BIOS_FIRMWARE, INSTALLED_AGENT])
    )
    monkeypatch.setattr(api, "produce", produce_mocked())

    checkhybridimage.check_hybrid_image()
    assert reporting.create_report.called == 1
    assert 'hybrid' in reporting.create_report.report_fields['title']
    assert api.produce.called == 1


@pytest.mark.parametrize('is_symlink, realpath_match, is_bios, agent_installed', [
    (False, True, True, True),
    (True, False, True, True),
    (True, True, False, True),
    (True, True, True, False),
])
def test_no_hybrid_image(monkeypatch, is_symlink, realpath_match, is_bios, agent_installed, tmpdir):
    grubenv_efi = tmpdir.join('grubenv_efi')
    grubenv_efi.write('grubenv')
    grubenv_efi_false = tmpdir.join('grubenv_efi_false')
    grubenv_efi.write('nope')
    grubenv_boot = tmpdir.join('grubenv_boot')

    grubenv_target = grubenv_efi if realpath_match else grubenv_efi_false

    if is_symlink:
        grubenv_boot.mksymlinkto(grubenv_target)

    firmw = BIOS_FIRMWARE if is_bios else EFI_FIRMWARE
    inst_rpms = INSTALLED_AGENT if agent_installed else NOT_INSTALLED_AGENT

    monkeypatch.setattr(checkhybridimage, 'BIOS_PATH', grubenv_boot.strpath)
    monkeypatch.setattr(checkhybridimage, 'EFI_PATH', grubenv_efi.strpath)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(
        api, 'current_actor', CurrentActorMocked(arch='x86_64', msgs=[firmw, inst_rpms])
    )
    monkeypatch.setattr(api, "produce", produce_mocked())

    checkhybridimage.check_hybrid_image()
    assert not reporting.create_report.called
    assert not api.produce.called
