import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecution
from leapp.libraries.actor import updategrubcore
from leapp.libraries.common import testutils
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import CalledProcessError
from leapp.models import FirmwareFacts
from leapp.reporting import Report

UPDATE_OK_TITLE = 'GRUB core successfully updated'
UPDATE_FAILED_TITLE = 'GRUB core update failed'


def raise_call_error(args=None):
    raise CalledProcessError(
        message='A Leapp Command Error occurred.',
        command=args,
        result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': 'fake', 'stderr': 'fake'}
    )


class run_mocked(object):
    def __init__(self, raise_err=False, raise_callback=raise_call_error):
        self.called = 0
        self.args = []
        self.raise_err = raise_err
        self.raise_callback = raise_callback

    def __call__(self, *args):
        self.called += 1
        self.args.append(args)
        if self.raise_err:
            self.raise_callback(args)


@pytest.mark.parametrize('devices', [['/dev/vda'], ['/dev/vda', '/dev/vdb']])
def test_update_grub(monkeypatch, devices):
    monkeypatch.setattr(reporting, 'create_report', testutils.create_report_mocked())
    monkeypatch.setattr(updategrubcore, 'run', run_mocked())
    updategrubcore.update_grub_core(devices)
    assert reporting.create_report.called
    assert UPDATE_OK_TITLE == reporting.create_report.reports[0]['title']
    assert all(dev in reporting.create_report.reports[0]['summary'] for dev in devices)


@pytest.mark.parametrize('devices', [['/dev/vda'], ['/dev/vda', '/dev/vdb']])
def test_update_grub_failed(monkeypatch, devices):
    monkeypatch.setattr(reporting, 'create_report', testutils.create_report_mocked())
    monkeypatch.setattr(updategrubcore, 'run', run_mocked(raise_err=True))
    updategrubcore.update_grub_core(devices)
    assert reporting.create_report.called
    assert UPDATE_FAILED_TITLE == reporting.create_report.reports[0]['title']
    assert all(dev in reporting.create_report.reports[0]['summary'] for dev in devices)
    assert 'successfully updated on ' not in reporting.create_report.reports[0]['summary']


def test_update_grub_partial_success(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', testutils.create_report_mocked())

    def run_mocked(args):
        if args == ['grub2-install', '/dev/vdb']:
            raise_call_error(args)
        else:
            assert args == ['grub2-install', '/dev/vda']

    monkeypatch.setattr(updategrubcore, 'run', run_mocked)

    devices = ['/dev/vda', '/dev/vdb']
    updategrubcore.update_grub_core(devices)

    assert reporting.create_report.called
    assert UPDATE_FAILED_TITLE == reporting.create_report.reports[0]['title']
    summary = reporting.create_report.reports[0]['summary']
    assert 'GRUB was successfully updated on the following devices: /dev/vda' in summary
    assert 'however GRUB update failed on the following devices: /dev/vdb' in summary


@pytest.mark.parametrize('msgs', [
    [],
    [FirmwareFacts(firmware='efi')]
])
def test_update_no_bios(monkeypatch, msgs):

    monkeypatch.setattr(reporting, 'create_report', testutils.create_report_mocked())
    monkeypatch.setattr(updategrubcore, 'run', run_mocked())

    curr_actor_mocked = testutils.CurrentActorMocked(msgs=msgs)
    monkeypatch.setattr(updategrubcore.api, 'current_actor', curr_actor_mocked)
    updategrubcore.process()
    assert not updategrubcore.run.called
    assert not reporting.create_report.called


def test_update_grub_nogrub_system_ibmz(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', testutils.create_report_mocked())
    monkeypatch.setattr(updategrubcore, 'run', run_mocked())

    msgs = [FirmwareFacts(firmware='bios')]
    curr_actor_mocked = testutils.CurrentActorMocked(arch=architecture.ARCH_S390X, msgs=msgs)
    monkeypatch.setattr(updategrubcore.api, 'current_actor', curr_actor_mocked)

    updategrubcore.process()
    assert not reporting.create_report.called
    assert not updategrubcore.run.called


def test_update_grub_nogrub_system(monkeypatch):
    def raise_call_oserror(dummy):
        # Note: grub2-probe is enough right now. If the implementation is changed,
        # the test will most likely start to fail and better mocking will be needed.
        raise OSError('File not found: grub2-probe')

    monkeypatch.setattr(reporting, 'create_report', testutils.create_report_mocked())
    monkeypatch.setattr(updategrubcore, 'run', run_mocked(raise_err=True, raise_callback=raise_call_oserror))

    msgs = [FirmwareFacts(firmware='bios')]
    curr_actor_mocked = testutils.CurrentActorMocked(arch=architecture.ARCH_X86_64, msgs=msgs)
    monkeypatch.setattr(updategrubcore.api, 'current_actor', curr_actor_mocked)

    with pytest.raises(StopActorExecution):
        updategrubcore.process()
    assert not reporting.create_report.called
