import pytest

from leapp import reporting
from leapp.libraries.actor.checkdnfpluginpath import check_dnf_pluginpath
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import DnfPluginPathDetected
from leapp.utils.report import is_inhibitor


@pytest.mark.parametrize('is_detected,should_report', [(False, False), (True, True)])
def test_check_dnf_pluginpath(monkeypatch, is_detected, should_report):
    actor_reports = create_report_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(reporting, 'create_report', actor_reports)

    dnf_pluginpath_detected = DnfPluginPathDetected(is_pluginpath_detected=is_detected)
    check_dnf_pluginpath(dnf_pluginpath_detected)

    assert actor_reports.called == should_report

    if should_report:
        assert is_inhibitor(actor_reports.report_fields)
