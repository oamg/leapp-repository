import pytest

from leapp import reporting
from leapp.libraries.actor import inhibitcgroupsv1
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import KernelCmdline, KernelCmdlineArg


@pytest.mark.parametrize(
    "cmdline_params", (
        ([KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="0")]),
        ([KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="false")]),
        ([KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="False")]),
        ([KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="no")]),
        (
            [
                KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="0"),
                KernelCmdlineArg(key="systemd.legacy_systemd_cgroup_controller", value="0"),
            ]
        ), (
            [
                KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="0"),
                KernelCmdlineArg(key="systemd.legacy_systemd_cgroup_controller", value="1"),
            ]
        )
    )
)
def test_inhibit_should_inhibit(monkeypatch, cmdline_params):
    curr_actor_mocked = CurrentActorMocked(msgs=[KernelCmdline(parameters=cmdline_params)])
    monkeypatch.setattr(api, "current_actor", curr_actor_mocked)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    inhibitcgroupsv1.process()

    assert reporting.create_report.called == 1
    report = reporting.create_report.reports[0]
    assert "cgroups-v1" in report["title"]
    assert reporting.Groups.INHIBITOR in report["groups"]

    command = [r for r in report["detail"]["remediations"] if r["type"] == "command"][0]
    assert "systemd.unified_cgroup_hierarchy" in command['context'][2]
    if len(cmdline_params) == 2:
        assert "systemd.legacy_systemd_cgroup_controller" in command['context'][2]


@pytest.mark.parametrize(
    "cmdline_params", (
        ([KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="1")]),
        ([KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="true")]),
        ([KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="True")]),
        ([KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="yes")]),
        ([KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value=None)]),
        (
            [
                KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="1"),
                KernelCmdlineArg(key="systemd.legacy_systemd_cgroup_controller", value="1"),
            ]
        ), (
            [
                KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="1"),
                KernelCmdlineArg(key="systemd.legacy_systemd_cgroup_controller", value="0"),
            ]
        ),
    )
)
def test_inhibit_should_not_inhibit(monkeypatch, cmdline_params):
    curr_actor_mocked = CurrentActorMocked(msgs=[KernelCmdline(parameters=cmdline_params)])
    monkeypatch.setattr(api, "current_actor", curr_actor_mocked)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    inhibitcgroupsv1.process()

    assert not reporting.create_report.called
