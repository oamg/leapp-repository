import pytest

from leapp import reporting
from leapp.libraries.actor import transitionsystemdservicesstates
from leapp.libraries.common.config import version
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


def test_filter_irrelevant_services_services_filtered():
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

    filtered = transitionsystemdservicesstates._filter_irrelevant_services(
        services_source, services_target
    )

    assert not filtered


def test_filter_irrelevant_services_services_not_filtered():
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

    filtered = transitionsystemdservicesstates._filter_irrelevant_services(
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
    """
    Test that reports are created and contain the right services
    """
    services_source = [
        SystemdServiceFile(name="rsyncd.service", state="enabled"),
        SystemdServiceFile(name="all_enabled.service", state="enabled"),
        SystemdServiceFile(name="newly_enabled.service", state="disabled"),
        SystemdServiceFile(name="enabled_by_preset.service", state="disabled"),
        SystemdServiceFile(name="enabled_despite_target_preset_disable.service", state="enabled"),
    ]
    presets_source = [
        SystemdServicePreset(service="rsyncd.service", state="enable"),
        SystemdServicePreset(service="all_enabled.service", state="enable"),
        SystemdServicePreset(service="newly_enabled.service", state="disable"),
        SystemdServicePreset(service="enabled_by_preset.service", state="disable"),
        SystemdServicePreset(service="enabled_despite_target_preset_disable.service", state="enable"),
    ]
    services_target = [
        SystemdServiceFile(name="rsyncd.service", state="disabled"),
        SystemdServiceFile(name="all_enabled.service", state="enabled"),
        SystemdServiceFile(name="newly_enabled.service", state="enabled"),
        SystemdServiceFile(name="enabled_by_preset.service", state="disabled"),
        SystemdServiceFile(name="enabled_despite_target_preset_disable.service", state="disabled"),
    ]
    presets_target = [
        SystemdServicePreset(service="rsyncd.service", state="enable"),
        SystemdServicePreset(service="all_enabled.service", state="enable"),
        SystemdServicePreset(service="newly_enabled.service", state="enable"),
        SystemdServicePreset(service="enabled_by_preset.service", state="enable"),
        SystemdServicePreset(service="enabled_despite_target_preset_disable.service", state="disable"),
    ]

    monkeypatch.setattr(
        api,
        "current_actor",
        CurrentActorMocked(
            msgs=[
                SystemdServicesInfoSource(service_files=services_source),
                SystemdServicesInfoTarget(service_files=services_target),
                SystemdServicesPresetInfoSource(presets=presets_source),
                SystemdServicesPresetInfoTarget(presets=presets_target),
            ]
        ),
    )
    monkeypatch.setattr(api, "produce", produce_mocked())
    created_reports = create_report_mocked()
    monkeypatch.setattr(reporting, "create_report", created_reports)

    transitionsystemdservicesstates.process()

    assert created_reports.called == 2
    reports = {r["title"]: r["summary"] for r in created_reports.reports}

    newly_enabled_summary = reports["Some systemd services were newly enabled"]
    assert "newly_enabled.service" in newly_enabled_summary
    assert "enabled_by_preset.service" in newly_enabled_summary
    for s in ["rsyncd.service", "all_enabled.service", "enabled_despite_target_preset_disable.service"]:
        assert s not in newly_enabled_summary

    kept_enabled_summary = reports["Previously enabled systemd services were kept enabled"]
    assert "enabled_despite_target_preset_disable.service" in kept_enabled_summary
    # rsyncd is covered by the generic part of the kept enabled report, not listed explicitly
    for s in ["rsyncd.service", "all_enabled.service", "newly_enabled.service", "enabled_by_preset.service"]:
        assert s not in kept_enabled_summary

    assert api.produce.called
    produced_tasks = api.produce.model_instances[0]
    assert produced_tasks.to_enable == [
        "rsyncd.service",
        "enabled_by_preset.service",
        "enabled_despite_target_preset_disable.service",
    ]
    assert produced_tasks.to_disable == []


@pytest.mark.parametrize(
    "services, expect_extended_summary",
    (
        (['explictly-enabled.service', 'explictly-enabled2.service'], True),
        (['explictly-enabled.service'], True),
        ([], False),
    ),
)
def test_report_kept_enabled(monkeypatch, services, expect_extended_summary):
    created_reports = create_report_mocked()
    monkeypatch.setattr(reporting, "create_report", created_reports)

    transitionsystemdservicesstates._report_kept_enabled(services)

    extended_summary_str = (
        "The following services were originally disabled by preset on the"
        " upgraded system and Leapp attempted to enable them"
    )

    assert created_reports.called == 1
    if expect_extended_summary:
        assert extended_summary_str in created_reports.report_fields["summary"]
        assert all(s in created_reports.report_fields['summary'] for s in services)
    else:
        assert extended_summary_str not in created_reports.report_fields["summary"]


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
    assert newly_enabled == ["test.service"]


@pytest.mark.parametrize(
    "newly_enabled, should_report",
    [
        (["test.service", "other.service"], True),
        ([], False),
    ]
)
def test_report_newly_enabled(monkeypatch, newly_enabled, should_report):
    created_reports = create_report_mocked()
    monkeypatch.setattr(reporting, "create_report", created_reports)

    transitionsystemdservicesstates._report_newly_enabled(newly_enabled)

    if should_report:
        assert created_reports.called == 1
        assert all(s in created_reports.report_fields["summary"] for s in newly_enabled)
    else:
        assert not created_reports.called


@pytest.mark.parametrize(
    "source_major_ver,expected", (
        (
            7,
            {
                'abc.service': 'enabled',
                'virtqemud.service': 'enabled',
                'virtlogd.service': 'disabled',
                'virtproxyd.service': 'masked',
            }
        ),
        (8, {'abc.service': 'enabled'}),
        (9, {'abc.service': 'enabled'}),
    )
)
def test_filter_ignored_services(monkeypatch, source_major_ver, expected):
    services = {
        'abc.service': 'enabled',
        'virtqemud.service': 'enabled',
        'virtlogd.service': 'disabled',
        'virtproxyd.service': 'masked',
    }
    monkeypatch.setattr(
        version,
        "get_source_major_version",
        lambda: source_major_ver,
    )
    transitionsystemdservicesstates._filter_ignored_services(services)
    assert services == expected
