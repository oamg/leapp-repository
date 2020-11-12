from leapp.reporting import create_report
from leapp import reporting
from leapp.libraries.common.tcpwrappersutils import config_applies_to_daemon


def check_config_supported(tcpwrap_facts, vsftpd_facts):
    bad_configs = [config.path for config in vsftpd_facts.configs if config.tcp_wrappers]
    if bad_configs and config_applies_to_daemon(tcpwrap_facts, 'vsftpd'):
        list_separator_fmt = '\n    - '
        create_report([
            reporting.Title('Unsupported vsftpd configuration'),
            reporting.Summary(
                    'tcp_wrappers support has been removed in RHEL-8. '
                    'Some configuration files set the tcp_wrappers option to true and '
                    'there is some vsftpd-related configuration in /etc/hosts.deny '
                    'or /etc/hosts.allow. Please migrate it manually. '
                    'The list of problematic configuration files:{}{}'.
                    format(
                        list_separator_fmt,
                        list_separator_fmt.join(bad_configs)
                    )
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.NETWORK, reporting.Groups.INHIBITOR]),
            reporting.ExternalLink(
                title='Replacing TCP Wrappers in RHEL 8',
                url='https://access.redhat.com/solutions/3906701'
            ),
            reporting.RelatedResource('package', 'tcp_wrappers'),
            reporting.RelatedResource('package', 'vsftpd'),
        ] + [reporting.RelatedResource('file', str(bc)) for bc in bad_configs])
