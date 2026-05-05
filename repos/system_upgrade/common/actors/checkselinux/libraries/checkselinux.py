import re

from leapp import reporting
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.common.distro import DISTRO_REPORT_NAMES
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import (
    KernelCmdline,
    KernelCmdlineArg,
    SELinuxFacts,
    SelinuxPermissiveDecision,
    SelinuxRelabelDecision,
    TargetKernelCmdlineArgTasks
)

DOC_URL = 'https://red.ht/rhel9-disabling-selinux'

_ENFORCING_ONE_ARG = KernelCmdlineArg(key='enforcing', value='1')


def _proc_cmdline_has_enforcing_one(kernel_cmdline):
    """
    Checks if the kernel command line contains enforcing=1.
    """
    if not kernel_cmdline:
        return False
    for param in kernel_cmdline.parameters:
        if param.key == 'enforcing' and param.value == '1':
            return True
    return False


def _parse_grubby_quoted_value(record):
    """
    Parses a grubby --info line, extracts the value after =, and
    removes any surrounding quotes so the kernel arguments can be processed reliably.
    """
    data = record.split('=', 1)[1]
    matches = re.match(r'^([\'"]?)(.*)\1$', data)
    return matches.group(2)


def _bootloader_entries_contain_enforcing_one():
    """
    Inspect every bootloader entry (grubby/BLS), not only the running kernel.
    """
    try:
        out = run(['/usr/sbin/grubby', '--info', 'ALL'], split=False)['stdout']
    except (OSError, CalledProcessError):
        api.current_logger().debug('grubby --info ALL failed; skipping bootloader enforcing=1 scan', exc_info=True)
        return False

    for line in out.splitlines():
        if line.startswith('args='):
            argstr = _parse_grubby_quoted_value(line)
            tokens = argstr.split()
            if 'enforcing=1' in tokens:
                return True
    return False


def _request_removal_of_enforcing_one_from_target_cmdline(kernel_cmdline):
    """
    Schedule stripping of enforcing=1 from all target boot entries (finalization phase).

    The upgrade workflow and dracut hook force permissive SELinux unless the kernel was
    booted with enforcing=1. If that parameter remains in any grub entry after upgrade,
    a later boot can force enforcing mode and break the upgraded system. The interim upgrade
    boot entry is configured with enforcing=0 and strips enforcing=1 when copied from the
    default entry; this scheduling ensures enforcing=1 is not kept on the upgraded system
    (see Checks phase here, application on ALL kernels in kernelcmdlineconfig).
    """
    in_proc = _proc_cmdline_has_enforcing_one(kernel_cmdline)
    in_bootloader = False if in_proc else _bootloader_entries_contain_enforcing_one()
    if not in_proc and not in_bootloader:
        return

    api.produce(TargetKernelCmdlineArgTasks(to_remove=[_ENFORCING_ONE_ARG]))
    reporting.create_report([
        reporting.Title('Kernel boot parameter enforcing=1 will be removed'),
        reporting.Summary(
            'The kernel parameter enforcing=1 forces SELinux enforcing mode at boot and overrides '
            'the permissive configuration used during the upgrade. Leapp will remove enforcing=1 from '
            'all boot loader entries during the upgrade finalization so it does not persist after the upgrade.'
        ),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.SELINUX, reporting.Groups.BOOT, reporting.Groups.KERNEL]),
    ])


def process():
    facts = next(api.consume(SELinuxFacts), None)
    if not facts:
        return

    kernel_cmdline = next(api.consume(KernelCmdline), None)
    _request_removal_of_enforcing_one_from_target_cmdline(kernel_cmdline)

    enabled = facts.enabled
    conf_status = facts.static_mode

    if conf_status == 'disabled':
        if get_target_major_version() == '9':
            api.produce(KernelCmdlineArg(key='selinux', value='0'))
            reporting.create_report([
                reporting.Title('LEAPP detected SELinux disabled in "/etc/selinux/config"'),
                reporting.Summary(
                    'On {target_distro} 9, disabling SELinux in "/etc/selinux/config" is no longer possible. '
                    'This way, the system starts with SELinux enabled but with no policy loaded. Leapp '
                    'will automatically disable SELinux using "SELINUX=0" kernel command line parameter. '
                    'However, it is strongly recommended to have SELinux enabled'.format_map(DISTRO_REPORT_NAMES)
                ),
                reporting.Severity(reporting.Severity.INFO),
                reporting.Groups([reporting.Groups.SELINUX]),
                reporting.RelatedResource('file', '/etc/selinux/config'),
                reporting.ExternalLink(url=DOC_URL, title='Disabling SELinux'),
            ])

        if enabled:
            reporting.create_report([
                reporting.Title('SElinux should be disabled based on the configuration file but it is enabled'),
                reporting.Summary(
                    'This message is to inform user about non-standard SElinux configuration. Please check '
                    '"/etc/selinux/config" to see whether the configuration is set as expected.'
                ),
                reporting.Severity(reporting.Severity.LOW),
                reporting.Groups([reporting.Groups.SELINUX, reporting.Groups.SECURITY])
            ])
        reporting.create_report([
            reporting.Title('SElinux disabled'),
            reporting.Summary('SElinux disabled, continuing...'),
            reporting.Groups([reporting.Groups.SELINUX, reporting.Groups.SECURITY])
        ])
        return

    if conf_status in ('enforcing', 'permissive'):
        api.produce(SelinuxRelabelDecision(set_relabel=True))
        reporting.create_report([
            reporting.Title('SElinux relabeling will be scheduled'),
            reporting.Summary('SElinux relabeling will be scheduled as the status is permissive/enforcing.'),
            reporting.Severity(reporting.Severity.INFO),
            reporting.Groups([reporting.Groups.SELINUX, reporting.Groups.SECURITY])
        ])

    if conf_status == 'enforcing':
        api.produce(SelinuxPermissiveDecision(
            set_permissive=True))
        reporting.create_report([
            reporting.Title('SElinux will be set to permissive mode'),
            reporting.Summary(
                'SElinux will be set to permissive mode. Current mode: enforcing. This action is '
                'required by the upgrade process to make sure the upgraded system can boot without '
                'beinig blocked by SElinux rules.'
            ),
            reporting.Severity(reporting.Severity.LOW),
            reporting.Remediation(hint=(
                'Make sure there are no SElinux related warnings after the upgrade and enable SElinux '
                'manually afterwards. Notice: You can ignore the "/root/tmp_leapp_py3" SElinux warnings.'
                )
            ),
            reporting.Groups([reporting.Groups.SELINUX, reporting.Groups.SECURITY])
        ])
