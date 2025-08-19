import pytest

from leapp import reporting
from leapp.libraries.actor.checkdnfpluginpath import check_dnf_pluginpath, perform_check
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import DnfPluginPathDetected
from leapp.utils.report import is_inhibitor


@pytest.mark.parametrize('is_detected', [False, True])
def test_check_dnf_pluginpath(monkeypatch, is_detected):
    actor_reports = create_report_mocked()
    msg = DnfPluginPathDetected(is_pluginpath_detected=is_detected)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[msg]))
    monkeypatch.setattr(reporting, 'create_report', actor_reports)

    perform_check()

    assert bool(actor_reports.called) == is_detected

    if is_detected:
        assert is_inhibitor(actor_reports.report_fields)


def test_perform_check_no_message_available(monkeypatch):
    """Test perform_check when no DnfPluginPathDetected message is available."""
    actor_reports = create_report_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(reporting, 'create_report', actor_reports)

    perform_check()

    assert not actor_reports.called
