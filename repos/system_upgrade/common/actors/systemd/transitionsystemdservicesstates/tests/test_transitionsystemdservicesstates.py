import pytest

from leapp import reporting
from leapp.libraries.actor import transitionsystemdservicesstates
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    SystemdServiceFile,
    SystemdServicePreset,
    SystemdServicesInfoSource,
    SystemdServicesInfoTarget,
    SystemdServicesPresetInfoSource,
    SystemdServicesPresetInfoTarget,
    SystemdServicesTasks
)


@pytest.mark.parametrize(
    "state_source, preset_source, preset_target, expected",
    (
        ["enabled", "disable", "enable", "enabled"],
        ["enabled", "disable", "disable", "enabled"],
        ["disabled", "disable", "disable", "disabled"],
        ["disabled", "disable", "enable", "enabled"],
        ["masked", "disable", "enable", "masked"],
        ["masked", "disable", "disable", "masked"],
        ["enabled", "enable", "enable", "enabled"],
        ["enabled", "enable", "disable", "enabled"],
        ["masked", "enable", "enable", "masked"],
        ["masked", "enable", "disable", "masked"],
        ["disabled", "enable", "enable", "disabled"],
        ["disabled", "enable", "disable", "disabled"],
    ),
)
def test_get_desired_service_state(
    state_source, preset_source, preset_target, expected
):
    target_state = transitionsystemdservicesstates._get_desired_service_state(
        state_source, preset_source, preset_target
    )

    assert target_state == expected


@pytest.mark.parametrize(
    "desired_state, state_target, expected",
    (
        ("enabled", "enabled", SystemdServicesTasks()),
        ("enabled", "disabled", SystemdServicesTasks(to_enable=["test.service"])),
        ("disabled", "enabled", SystemdServicesTasks(to_disable=["test.service"])),
        ("disabled", "disabled", SystemdServicesTasks()),
    ),
)
def test_get_service_task(monkeypatch, desired_state, state_target, expected):
    def _get_desired_service_state_mocked(*args):
        return desired_state

    monkeypatch.setattr(
        transitionsystemdservicesstates,
        "_get_desired_service_state",
        _get_desired_service_state_mocked,
    )

    tasks = SystemdServicesTasks()
    transitionsystemdservicesstates._get_service_task(
        "test.service", desired_state, state_target, tasks
    )
    assert tasks == expected


def test_filter_services_services_filtered():
    services_source = {
        "test2.service": "static",
        "test3.service": "masked",
        "test4.service": "indirect",
        "test5.service": "indirect",
        "test6.service": "indirect",
    }
    services_target = [
        SystemdServiceFile(name="test1.service", state="enabled"),
        SystemdServiceFile(name="test2.service", state="masked"),
        SystemdServiceFile(name="test3.service", state="indirect"),
        SystemdServiceFile(name="test4.service", state="static"),
        SystemdServiceFile(name="test5.service", state="generated"),
        SystemdServiceFile(name="test6.service", state="masked-runtime"),
    ]

    filtered = transitionsystemdservicesstates._filter_services(
        services_source, services_target
    )

    assert not filtered


def test_filter_services_services_not_filtered():
    services_source = {
        "test1.service": "enabled",
        "test2.service": "disabled",
        "test3.service": "static",
        "test4.service": "indirect",
    }
    services_target = [
        SystemdServiceFile(name="test1.service", state="enabled"),
        SystemdServiceFile(name="test2.service", state="disabled"),
        SystemdServiceFile(name="test3.service", state="enabled-runtime"),
        SystemdServiceFile(name="test4.service", state="enabled"),
    ]

    filtered = transitionsystemdservicesstates._filter_services(
        services_source, services_target
    )

    assert len(filtered) == len(services_target)


@pytest.mark.parametrize(
    "presets",
    [
        dict(),
        {"other.service": "enable"},
    ],
)
def test_service_preset_missing_presets(presets):
    preset = transitionsystemdservicesstates._get_service_preset(
        "test.service", presets
    )
    assert preset == "disable"


def test_tasks_produced_reports_created(monkeypatch):
    services_source = [
        SystemdServiceFile(name="rsyncd.service", state="enabled"),
        SystemdServiceFile(name="test.service", state="enabled"),
    ]
    service_info_source = SystemdServicesInfoSource(service_files=services_source)

    presets_source = [
        SystemdServicePreset(service="rsyncd.service", state="enable"),
        SystemdServicePreset(service="test.service", state="enable"),
    ]
    preset_info_source = SystemdServicesPresetInfoSource(presets=presets_source)

    services_target = [
        SystemdServiceFile(name="rsyncd.service", state="disabled"),
        SystemdServiceFile(name="test.service", state="enabled"),
    ]
    service_info_target = SystemdServicesInfoTarget(service_files=services_target)

    presets_target = [
        SystemdServicePreset(service="rsyncd.service", state="enable"),
        SystemdServicePreset(service="test.service", state="enable"),
    ]
    preset_info_target = SystemdServicesPresetInfoTarget(presets=presets_target)

    monkeypatch.setattr(
        api,
        "current_actor",
        CurrentActorMocked(
            msgs=[
                service_info_source,
                service_info_target,
                preset_info_source,
                preset_info_target,
            ]
        ),
    )
    monkeypatch.setattr(api, "produce", produce_mocked())
    created_reports = create_report_mocked()
    monkeypatch.setattr(reporting, "create_report", created_reports)

    expected_tasks = SystemdServicesTasks(to_enable=["rsyncd.service"], to_disable=[])
    transitionsystemdservicesstates.process()

    assert created_reports.called == 2
    assert api.produce.called
    assert api.produce.model_instances[0].to_enable == expected_tasks.to_enable
    assert api.produce.model_instances[0].to_disable == expected_tasks.to_disable


def test_report_kept_enabled(monkeypatch):
    created_reports = create_report_mocked()
    monkeypatch.setattr(reporting, "create_report", created_reports)

    tasks = SystemdServicesTasks(
        to_enable=["test.service", "other.service"], to_disable=["another.service"]
    )
    transitionsystemdservicesstates._report_kept_enabled(tasks)

    assert created_reports.called
    assert all([s in created_reports.report_fields["summary"] for s in tasks.to_enable])


def test_get_newly_enabled():
    services_source = {
        "test.service": "disabled",
        "other.service": "enabled",
        "another.service": "enabled",
    }
    desired_states = {
        "test.service": "enabled",
        "other.service": "enabled",
        "another.service": "disabled",
    }

    newly_enabled = transitionsystemdservicesstates._get_newly_enabled(
        services_source, desired_states
    )
    assert newly_enabled == ['test.service']


def test_report_newly_enabled(monkeypatch):
    created_reports = create_report_mocked()
    monkeypatch.setattr(reporting, "create_report", created_reports)

    newly_enabled = ["test.service", "other.service"]
    transitionsystemdservicesstates._report_newly_enabled(newly_enabled)

    assert created_reports.called
    assert all([s in created_reports.report_fields["summary"] for s in newly_enabled])
