from leapp import reporting
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.stdlib import api
from leapp.models import KernelCmdlineArg, SELinuxFacts, SelinuxPermissiveDecision, SelinuxRelabelDecision

DOC_URL = 'https://red.ht/rhel9-disabling-selinux'


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
                    'On RHEL 9, disabling SELinux in "/etc/selinux/config" is no longer possible. '
                    'This way, the system starts with SELinux enabled but with no policy loaded. LEAPP '
                    'will automatically disable SELinux using "SELINUX=0" kernel command line parameter. '
                    'However, Red Hat strongly recommends to have SELinux enabled'
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
