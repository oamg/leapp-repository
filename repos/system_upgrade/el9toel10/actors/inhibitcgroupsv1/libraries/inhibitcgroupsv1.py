from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import KernelCmdline


def process():
    kernel_cmdline = next(api.consume(KernelCmdline), None)
    if not kernel_cmdline:
        # really unlikely
        raise StopActorExecutionError("Did not receive any KernelCmdline messages.")

    unified_hierarchy = True  # default since RHEL 9
    legacy_controller_present = False
    for param in kernel_cmdline.parameters:
        if param.key == "systemd.unified_cgroup_hierarchy":
            if param.value is not None and param.value.lower() in ("0", "false", "no"):
                unified_hierarchy = False
        if param.key == "systemd.legacy_systemd_cgroup_controller":
            # no matter the value, it should be removed
            # it has no effect when unified hierarchy is enabled
            legacy_controller_present = True

    if unified_hierarchy:
        api.current_logger().debug("cgroups-v2 already in use, nothing to do, skipping.")
        return

    remediation_cmd_args = ["systemd.unified_cgroup_hierarchy"]
    if legacy_controller_present:
        remediation_cmd_args.append('systemd.legacy_systemd_cgroup_controller')

    summary = (
        "Leapp detected cgroups-v1 is enabled on the system."
        " The support of cgroups-v1 was deprecated in RHEL 9 and is removed in RHEL 10."
        " Software requiring cgroups-v1 might not work correctly or at all on RHEL 10."
    )
    reporting.create_report(
        [
            reporting.Title("cgroups-v1 enabled on the system"),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR, reporting.Groups.KERNEL]),
            reporting.RelatedResource("package", "systemd"),
            reporting.Remediation(
                hint="Make sure no third party software requires cgroups-v1 and switch to cgroups-v2.",
                # remove the args from commandline, the defaults are the desired values
                commands=[
                    [
                        "grubby",
                        "--update-kernel=ALL",
                        '--remove-args="{}"'.format(" ".join(remediation_cmd_args)),
                    ],
                ],
            ),
        ]
    )
