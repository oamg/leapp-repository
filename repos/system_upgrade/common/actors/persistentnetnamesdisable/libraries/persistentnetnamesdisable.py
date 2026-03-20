import re

from leapp import reporting
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.stdlib import api
from leapp.models import (
    KernelCmdlineArg,
    PersistentNetNamesFacts,
    TargetKernelCmdlineArgTasks,
    UpgradeKernelCmdlineArgTasks
)
from leapp.reporting import create_report


def ethX_count(interfaces):
    """
    Count how many network interfaces with ethX naming is present.
    """
    ethX = re.compile('^eth[0-9]+$')
    count = 0

    for i in interfaces:
        if ethX.match(i.name):
            count = count + 1
    return count


def single_eth0(interfaces):
    return len(interfaces) == 1 and interfaces[0].name == 'eth0'


def disable_persistent_naming():
    api.current_logger().info(
        "Single eth0 network interface detected."
        " Appending 'net.ifnames=0' for the target system kernel commandline"
    )
    k_arg = KernelCmdlineArg(key='net.ifnames', value='0')
    api.produce(UpgradeKernelCmdlineArgTasks(to_add=[k_arg]))
    api.produce(TargetKernelCmdlineArgTasks(to_add=[k_arg]))


def report_ethX_ifaces():
    report_entries = [
        reporting.Title('Unsupported network configuration'),
        reporting.Summary(
            'Detected multiple physical network interfaces where one or more'
            ' use kernel naming (e.g. eth0). Upgrade process cannot continue'
            ' because stability of names can not be guaranteed.'
        ),
        reporting.ExternalLink(
            title='How to Perform an In-Place Upgrade when Using Kernel-Assigned NIC Names',
            url='https://access.redhat.com/solutions/4067471'
        ),
        reporting.Remediation(
            hint='Rename all ethX network interfaces following the attached KB solution article.'
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.NETWORK]),
        reporting.Groups([reporting.Groups.INHIBITOR])
    ]

    if get_target_major_version() == '9':
        report_entries.append(
            reporting.ExternalLink(
                title='RHEL 8 to RHEL 9: inplace upgrade fails at '
                      '"Network configuration for unsupported device types detected"',
                url='https://access.redhat.com/solutions/7009239'
            )
        )

    create_report(report_entries)


def process():
    interfaces = next(api.consume(PersistentNetNamesFacts)).interfaces

    if single_eth0(interfaces):
        disable_persistent_naming()
        return

    if len(interfaces) > 1 and ethX_count(interfaces):
        report_ethX_ifaces()
