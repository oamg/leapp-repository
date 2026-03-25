import re

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config.version import get_source_major_version, get_target_major_version
from leapp.libraries.stdlib import api
from leapp.models import (
    KernelCmdline,
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


def is_kernel_arg_present(key, value=None):
    """
    Return True if requested argument is set in kernel cmdline. Return False otherwise.

    If the `value` is specified, check also whether the specific value is set.
    The function consumes :class:`KernelCmdline`.

    :param key: The kernel argument to search for
    :type key: str
    :param value: If string is specified, check for a specific string as well.
    :type value: str|None
    :rtype: bool
    """
    # NOTE(pstodulk): with small update a possible candidate to move into the
    # kernel shared library. For now, keeping it just in this actor.
    k_cmdline = next(api.consume(KernelCmdline), None)
    if not k_cmdline:
        # NOTE(pstodulk): this hypothetical situation, skipping coverage by
        # unit tests
        raise StopActorExecutionError(
            message='Missing information about current kernel command line.',
            details={
                'details': 'Missing the KernelCmdline message.'
            }
        )

    for k_arg in k_cmdline.parameters:
        if k_arg.key != key:
            continue
        if value is None or k_arg.value == value:
            return True
    return False


def disable_persistent_naming():
    api.current_logger().info(
        "Single eth0 network interface detected."
        " Appending 'net.ifnames=0' for the target system kernel commandline"
    )
    k_arg = KernelCmdlineArg(key='net.ifnames', value='0')
    api.produce(UpgradeKernelCmdlineArgTasks(to_add=[k_arg]))
    api.produce(TargetKernelCmdlineArgTasks(to_add=[k_arg]))


def report_ethX_ifaces():
    url_title_kb = 'How to Perform an In-Place Upgrade when Using Kernel-Assigned NIC Names'
    hint_text = f'Rename all ethX network interfaces following the "{url_title_kb}" solution article.'
    report_external_links = [
        reporting.ExternalLink(
            title=url_title_kb,
            url='https://access.redhat.com/solutions/4067471'
        )
    ]
    if not is_kernel_arg_present('net.naming-scheme') and not is_kernel_arg_present('net.ifnames', '0'):
        hint_text += (
            ' If the detected ethX interfaces are not manually configured, it is'
            ' possible that new names were not assigned due to a naming conflict'
            ' in the current `net.naming-scheme`. This can be resolved by'
            ' configuring a newer naming scheme via the kernel argument.'
            ' For more information, see "Implementing consistent network interface naming".'
        )

        # NOTE(pstodulk): the link is covered for RHEL 8, 9, 10
        report_external_links.append(reporting.ExternalLink(
            title='Implementing consistent network interface naming',
            url='https://red.ht/rhel-{}-consistent-nic-naming'.format(get_source_major_version())
        ))
    if get_target_major_version() == '9':
        report_external_links.append(
            reporting.ExternalLink(
                title='RHEL 8 to RHEL 9: inplace upgrade fails at '
                      '"Network configuration for unsupported device types detected"',
                url='https://access.redhat.com/solutions/7009239'
            )
        )

    report_entries = [
        reporting.Title('Unsupported network configuration'),
        reporting.Summary(
            'Detected multiple physical network interfaces where one or more'
            ' use kernel naming (e.g. eth0). Upgrade process cannot continue'
            ' because stability of names can not be guaranteed.'
        ),
        reporting.Remediation(hint=hint_text),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.NETWORK]),
        reporting.Groups([reporting.Groups.INHIBITOR])
    ] + report_external_links

    create_report(report_entries)


def process():
    interfaces = next(api.consume(PersistentNetNamesFacts)).interfaces

    if single_eth0(interfaces):
        disable_persistent_naming()
        return

    if len(interfaces) > 1 and ethX_count(interfaces):
        report_ethX_ifaces()
