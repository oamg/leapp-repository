from leapp.libraries.common.reporting import report_with_links
from leapp.libraries.common.tcpwrappersutils import config_applies_to_daemon


def check_config_supported(tcpwrap_facts, vsftpd_facts):
    bad_configs = [config.path for config in vsftpd_facts.configs if config.tcp_wrappers]
    if len(bad_configs) > 0 and config_applies_to_daemon(tcpwrap_facts, 'vsftpd'):
        list_separator_fmt = '\n    - '
        report_with_links(title='Unsupported vsftpd configuration',
                          summary=('tcp_wrappers support has been removed in RHEL-8. '
                                   'Some configuration files set the tcp_wrappers option to true and '
                                   'there is some vsftpd-related configuration in /etc/hosts.deny '
                                   'or /etc/hosts.allow. Please migrate it manually. '
                                   'The list of problematic configuration files:{}{}'
                                   ).format(list_separator_fmt,
                                            list_separator_fmt.join(bad_configs)),
                          links=[{'title': 'Replacing TCP Wrappers in RHEL 8',
                                  'href': 'https://access.redhat.com/solutions/3906701'}],
                          severity='high',
                          flags=['inhibitor'])
