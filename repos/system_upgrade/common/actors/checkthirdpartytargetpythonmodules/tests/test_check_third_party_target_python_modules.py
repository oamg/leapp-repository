import pytest

from leapp import reporting
from leapp.libraries.actor import checkthirdpartytargetpythonmodules
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import ThirdPartyTargetPythonModules


def test_perform_check_no_message_available(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[]))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    checkthirdpartytargetpythonmodules.perform_check()

    assert not reporting.create_report.called


def test_perform_check_empty_lists(monkeypatch):
    msg = ThirdPartyTargetPythonModules(
        target_python='python3.9',
        third_party_modules=[],
        third_party_rpm_names=[]
    )

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[msg]))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    checkthirdpartytargetpythonmodules.perform_check()

    assert not reporting.create_report.called


def test_perform_check_with_third_party_modules(monkeypatch):
    msg = ThirdPartyTargetPythonModules(
        target_python='python3.9',
        third_party_modules=['third_party_module'],
        third_party_rpm_names=['third_party_rpm']
    )

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[msg]))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    checkthirdpartytargetpythonmodules.perform_check()

    assert reporting.create_report.called
