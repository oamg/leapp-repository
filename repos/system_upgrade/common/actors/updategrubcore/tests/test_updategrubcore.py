import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecution
from leapp.libraries.actor import updategrubcore
from leapp.libraries.common import testutils
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import UpdateGrub
from leapp.reporting import Report

UPDATE_OK_TITLE = 'GRUB core successfully updated'
UPDATE_FAILED_TITLE = 'GRUB core update failed'


def raise_call_error(args=None):
    raise CalledProcessError(
        message='A Leapp Command Error occured.',
        command=args,
        result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': 'fake', 'stderr': 'fake'}
    )


class run_mocked(object):
    def __init__(self, raise_err=False):
        self.called = 0
        self.args = []
        self.raise_err = raise_err

    def __call__(self, *args):
        self.called += 1
        self.args.append(args)
        if self.raise_err:
            raise_call_error(args)


def test_update_grub(monkeypatch):
    monkeypatch.setattr(api, 'consume', lambda x: iter([UpdateGrub(grub_device='/dev/vda')]))
    monkeypatch.setattr(reporting, "create_report", testutils.create_report_mocked())
    monkeypatch.setattr(updategrubcore, 'run', run_mocked())
    updategrubcore.update_grub_core('/dev/vda')
    assert reporting.create_report.called
    assert UPDATE_OK_TITLE == reporting.create_report.report_fields['title']


def test_update_grub_failed(monkeypatch):
    monkeypatch.setattr(api, 'consume', lambda x: iter([UpdateGrub(grub_device='/dev/vda')]))
    monkeypatch.setattr(reporting, "create_report", testutils.create_report_mocked())
    monkeypatch.setattr(updategrubcore, 'run', run_mocked(raise_err=True))
    with pytest.raises(StopActorExecution):
        updategrubcore.update_grub_core('/dev/vda')
    assert reporting.create_report.called
    assert UPDATE_FAILED_TITLE == reporting.create_report.report_fields['title']


def test_update_grub_negative(current_actor_context):
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
