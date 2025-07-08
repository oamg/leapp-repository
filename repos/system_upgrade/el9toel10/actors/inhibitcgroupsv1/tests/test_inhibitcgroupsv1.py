import pytest

from leapp import reporting
from leapp.libraries.actor import inhibitcgroupsv1
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import KernelCmdline, KernelCmdlineArg


@pytest.mark.parametrize(
    "cmdline_params,should_inhibit", (
        ([KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="0")], True),
        ([KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="1")], False),
        ([KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="false")], True,),
        ([KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="true")], False,),
        (
            [
                KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="0"),
                KernelCmdlineArg(key="systemd.legacy_systemd_cgroup_controller", value="0"),
            ],
            True,
        ), (
            [
                KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="0"),
                KernelCmdlineArg(key="systemd.legacy_systemd_cgroup_controller", value="1"),
            ],
            True,
        ), (
            [
                KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="1"),
                KernelCmdlineArg(key="systemd.legacy_systemd_cgroup_controller", value="1"),
            ],
            False,
        ), (
            [
                KernelCmdlineArg(key="systemd.unified_cgroup_hierarchy", value="1"),
                KernelCmdlineArg(key="systemd.legacy_systemd_cgroup_controller", value="1"),
            ],
            False,
        ),
    )
)
def test_inhibit_v1(monkeypatch, cmdline_params, should_inhibit):
    curr_actor_mocked = CurrentActorMocked(msgs=[KernelCmdline(parameters=cmdline_params)])
    monkeypatch.setattr(api, "current_actor", curr_actor_mocked)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    inhibitcgroupsv1.process()

    if should_inhibit:
        assert reporting.create_report.called == 1
        assert "cgroups-v1" in reporting.create_report.reports[0]["title"]
        assert (
            reporting.Groups.INHIBITOR in reporting.create_report.reports[0]["groups"]
        )
    else:
        assert not reporting.create_report.called
