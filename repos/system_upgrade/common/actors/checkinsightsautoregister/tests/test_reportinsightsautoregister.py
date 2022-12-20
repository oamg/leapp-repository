import pytest

from leapp import reporting
from leapp.libraries.actor import checkinsightsautoregister
from leapp.libraries.common import rhsm
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api


@pytest.mark.parametrize(
    ("skip_rhsm", "no_register", "should_report"),
    [
        (False, False, True),
        (False, True, False),
        (True, False, False),
        (True, True, False),
    ],
)
def test_should_report(monkeypatch, skip_rhsm, no_register, should_report):

    monkeypatch.setattr(rhsm, "skip_rhsm", lambda: skip_rhsm)
    monkeypatch.setattr(
        api,
        "current_actor",
        CurrentActorMocked(
            envars={"LEAPP_NO_INSIGHTS_REGISTER": "1" if no_register else "0"}
        ),
    )

    def ensure_package_mocked(package):
        assert package == checkinsightsautoregister.INSIGHTS_CLIENT_PKG
        return False

    monkeypatch.setattr(
        checkinsightsautoregister, "_ensure_package", ensure_package_mocked
    )

    called = [False]

    def _report_registration_info_mocked(_):
        called[0] = True

    monkeypatch.setattr(
        checkinsightsautoregister,
        "_report_registration_info",
        _report_registration_info_mocked,
    )

    checkinsightsautoregister.process()

    assert called[0] == should_report


@pytest.mark.parametrize(
    "already_installed, should_install", [(True, False), (False, True)]
)
def test_install_task_produced(monkeypatch, already_installed, should_install):

    def has_package_mocked(*args, **kwargs):
        return already_installed

    monkeypatch.setattr(checkinsightsautoregister, "has_package", has_package_mocked)
    monkeypatch.setattr(api, "produce", produce_mocked())

    checkinsightsautoregister._ensure_package(
        checkinsightsautoregister.INSIGHTS_CLIENT_PKG
    )

    assert api.produce.called == should_install


@pytest.mark.parametrize("installing_client", (True, False))
def test_report_created(monkeypatch, installing_client):

    created_reports = create_report_mocked()
    monkeypatch.setattr(reporting, "create_report", created_reports)

    checkinsightsautoregister._report_registration_info(installing_client)

    assert created_reports.called
