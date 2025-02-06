import os

import pytest

from leapp import reporting
from leapp.libraries.actor import scanhybridimage
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked, produce_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import FirmwareFacts, HybridImageAzure, InstalledRPM, RPM

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


def raise_call_error(args=None):
    raise CalledProcessError(
        message='A Leapp Command Error occurred.',
        command=args,
        result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': 'fake', 'stderr': 'fake'}
    )


class run_mocked(object):
    def __init__(self, hypervisor='', raise_err=False):
        self.hypervisor = hypervisor
        self.called = 0
        self.args = []
        self.raise_err = raise_err

    def __call__(self, *args):  # pylint: disable=inconsistent-return-statements
        self.called += 1
        self.args.append(args)

        if self.raise_err:
            raise_call_error(args)

        if args[0] == ['systemd-detect-virt']:
            return {'stdout': self.hypervisor}

        raise AttributeError("Unexpected command supplied!")


@pytest.mark.parametrize('hypervisor, expected', [('none', False), ('microsoft', True)])
def test_is_running_on_azure_hypervisor(monkeypatch, hypervisor, expected):
    monkeypatch.setattr(scanhybridimage, 'run', run_mocked(hypervisor))

    assert scanhybridimage.is_running_on_azure_hypervisor() == expected


def test_is_running_on_azure_hypervisor_error(monkeypatch):
    monkeypatch.setattr(scanhybridimage, 'run', run_mocked('microsoft', raise_err=True))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    result = scanhybridimage.is_running_on_azure_hypervisor()

    assert result is False
    assert any('Unable to detect' in msg for msg in api.current_logger.warnmsg)


@pytest.mark.parametrize('is_symlink', [True, False])
@pytest.mark.parametrize('realpath_match', [True, False])
def test_is_grubenv_symlink_to_efi(monkeypatch, is_symlink, realpath_match):
    grubenv_efi_false = '/other/grub/grubenv'

    monkeypatch.setattr(scanhybridimage, 'GRUBENV_BIOS_PATH', BIOS_PATH)
    monkeypatch.setattr(scanhybridimage, 'GRUBENV_EFI_PATH', EFI_PATH)

    monkeypatch.setattr(os.path, 'islink', lambda path: is_symlink)

    def mocked_realpath(path):
        if realpath_match:
            return EFI_PATH

        return grubenv_efi_false if path == EFI_PATH else EFI_PATH

    monkeypatch.setattr(os.path, 'realpath', mocked_realpath)

    result = scanhybridimage.is_grubenv_symlink_to_efi()

    assert result == (is_symlink and realpath_match)


@pytest.mark.parametrize('is_bios', [True, False])
@pytest.mark.parametrize('has_efi_partition', [True, False])
@pytest.mark.parametrize('agent_installed', [True, False])
@pytest.mark.parametrize('is_microsoft', [True, False])
@pytest.mark.parametrize('is_symlink', [True, False])
def test_hybrid_image(monkeypatch, tmpdir, is_bios, has_efi_partition, agent_installed, is_microsoft, is_symlink):
    should_produce = (is_microsoft and is_bios and has_efi_partition) or (agent_installed and is_bios)

    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    msgs = [
        BIOS_FIRMWARE if is_bios else EFI_FIRMWARE,
        INSTALLED_AGENT if agent_installed else NOT_INSTALLED_AGENT
    ]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(scanhybridimage, 'has_efi_partition', lambda: has_efi_partition)
    monkeypatch.setattr(scanhybridimage, 'is_running_on_azure_hypervisor', lambda: is_microsoft)
    monkeypatch.setattr(scanhybridimage, 'is_grubenv_symlink_to_efi', lambda: is_symlink)

    scanhybridimage.scan_hybrid_image()

    if should_produce:
        assert api.produce.called == 1
        assert HybridImageAzure(grubenv_is_symlink_to_efi=is_symlink) in api.produce.model_instances
    else:
        assert not api.produce.called
