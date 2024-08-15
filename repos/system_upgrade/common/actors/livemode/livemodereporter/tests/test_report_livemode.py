import pytest

from leapp import reporting
from leapp.libraries.actor import report_livemode as report_livemode_lib
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import LiveModeConfig


@pytest.mark.parametrize(
    ('livemode_config', 'should_report'),
    (
        (LiveModeConfig(is_enabled=True, squashfs_fullpath='path'), True),
        (LiveModeConfig(is_enabled=False, squashfs_fullpath='path'), False),
        (None, False),
    )
)
def test_report_livemode(monkeypatch, livemode_config, should_report):
    messages = [livemode_config] if livemode_config else []
    mocked_actor = CurrentActorMocked(msgs=messages)
    monkeypatch.setattr(api, 'current_actor', mocked_actor)

    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    report_livemode_lib.report_live_mode_if_enabled()

    if should_report:
        assert reporting.create_report.called == 1
    else:
        assert reporting.create_report.called == 0
