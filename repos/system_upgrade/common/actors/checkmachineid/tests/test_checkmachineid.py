import pytest

from leapp import reporting
from leapp.libraries.actor import checkmachineid
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import MachineIdInfo
from leapp.utils.report import is_inhibitor

_VALID_MACHINE_ID = 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4'


@pytest.mark.parametrize('machine_id,should_inhibit', [
    (None, True),
    ('', True),
    ('abc123', True),
    ('a' * 33, True),
    ('z' * 32, True),
    ('A1B2C3D4E5F6A1B2C3D4E5F6A1B2C3D4', True),
    (_VALID_MACHINE_ID, False),
])
def test_check_machine_id(monkeypatch, machine_id, should_inhibit):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=[MachineIdInfo(machine_id=machine_id)]
    ))
    checkmachineid.process()
    assert bool(reporting.create_report.called) == should_inhibit
    if should_inhibit:
        assert is_inhibitor(reporting.create_report.report_fields)


def test_check_machine_id_missing_message(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[]))
    checkmachineid.process()
    assert not reporting.create_report.called
