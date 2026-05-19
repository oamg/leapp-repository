from leapp import reporting
from leapp.libraries.common.config import architecture
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.common.distro import DISTRO_REPORT_NAMES
from leapp.libraries.stdlib import api
from leapp.models import (
    KernelCmdline,
    KernelCmdlineArg,
    SELinuxFacts,
    SelinuxPermissiveDecision,
    SelinuxRelabelDecision,
    TargetKernelCmdlineArgTasks,
    UpgradeKernelCmdlineArgTasks
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


def _request_removal_of_enforcing_one():
    """
    Schedule stripping of enforcing=1 from the upgrade and target boot entries.

    The upgrade workflow runs with SELinux permissive, but if enforcing=1 is present on
    the running kernel or in any bootloader entry it can override that. We produce:

    * ``UpgradeKernelCmdlineArgTasks`` so the interim upgrade boot entry drops enforcing=1
      (consumed by ``addupgradebootentry``).
    * ``TargetKernelCmdlineArgTasks`` so the target kernel entry and the default kernel
      command line configuration are updated during finalization (consumed by
      ``kernelcmdlineconfig``), ensuring that future kernels also omit enforcing=1.

    Original boot entries for existing (non-target) kernels are left untouched.

    ``SELinuxFacts.enforcing_via_any_cmdline`` is populated earlier by the
    ``systemfacts`` actor.
    """
    arch = api.current_actor().configuration.architecture
    arch_msg = ' Then make sure to run zipl to update the boot menu.' if arch == architecture.ARCH_S390X else ''
    doc_url = 'https://red.ht/rhel-{}-configure-kernel-cmdline'.format(get_target_major_version())
    hint = (
        'After the upgrade, add the `enforcing=1` kernel command line argument back if it is wanted.'
        ' Run "grubby --update-kernel=ALL --args=enforcing=1" to enable enforcing on all boot entries'
        f' and set it as default.{arch_msg}'
        ' Follow the documentation in the attached link for more details.'
    )

    api.produce(UpgradeKernelCmdlineArgTasks(to_remove=[_ENFORCING_ONE_ARG]))
    api.produce(TargetKernelCmdlineArgTasks(to_remove=[_ENFORCING_ONE_ARG]))
    reporting.create_report([
        reporting.Title('Kernel boot parameter enforcing=1 will be removed'),
        reporting.Summary(
            'The kernel parameter enforcing=1 forces SELinux enforcing mode at boot and overrides '
            'the permissive configuration used during the upgrade. Leapp will remove enforcing=1 from '
            'the upgrade and target kernel boot entries and update the default kernel command line '
            'configuration so it does not persist after the upgrade. Existing boot entries for other '
            'kernels will not be modified.'
        ),
        reporting.Remediation(hint=hint),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([
            reporting.Groups.SELINUX,
            reporting.Groups.BOOT,
            reporting.Groups.KERNEL,
            reporting.Groups.POST,
        ]),
        reporting.ExternalLink(url=doc_url, title='Configuring kernel command line parameters'),
    ])


def process():
    facts = next(api.consume(SELinuxFacts), None)
    if not facts:
        return

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

    kernel_cmdline = next(api.consume(KernelCmdline), None)
    if _proc_cmdline_has_enforcing_one(kernel_cmdline) or facts.enforcing_via_any_cmdline:
        _request_removal_of_enforcing_one()

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
