from leapp.actors import Actor
from leapp.models import SSSDConfig
from leapp import reporting
from leapp.reporting import Report, create_report
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag


COMMON_REPORT_GROUPS = [reporting.Groups.AUTHENTICATION, reporting.Groups.SECURITY]

related = [
    reporting.RelatedResource('package', 'sssd'),
    reporting.RelatedResource('file', '/etc/sssd/sssd.conf')
]


class SSSDCheck(Actor):
    """
    Check SSSD configuration for changes in RHEL8 and report them.

    These changes are:
    - id_provider=local is no longer supported and will be ignored
    - ldap_groups_use_matching_rule_in_chain was removed and will be ignored
    - ldap_initgroups_use_matching_rule_in_chain was removed and will be ignored
    - ldap_sudo_include_regexp changed default from true to false
    """

    name = 'sssd_check'
    consumes = (SSSDConfig,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        model = next(self.consume(SSSDConfig), None)
        if not model:
            return

        for domain in model.domains:
            if 'local_provider' in domain.options:
                self.reportLocalProvider(domain)

            if 'groups_chain' in domain.options:
                self.reportRemovedOption(domain, 'ldap_groups_use_matching_rule_in_chain')

            if 'initgroups_chain' in domain.options:
                self.reportRemovedOption(domain, 'ldap_initgroups_use_matching_rule_in_chain')

            if 'sudo_regexp' in domain.options:
                self.reportSudoRegexp(domain)

    def reportLocalProvider(self, domain):
        create_report([
            reporting.Title('SSSD Domain "%s": local provider is no longer '
                            'supported and the domain will be ignored.' % domain),
            reporting.Summary('Local provider is no longer supported.'),
            reporting.Groups(COMMON_REPORT_GROUPS),
            reporting.Severity(reporting.Severity.MEDIUM)
        ] + related)

    def reportRemovedOption(self, domain, option):
        create_report([
            reporting.Title('SSSD Domain "%s": option %s has no longer '
                            'any effect' % (domain, option)),
            reporting.Summary('Option %s was removed and it will be ignored.' % option),
            reporting.Groups(COMMON_REPORT_GROUPS),
            reporting.Severity(reporting.Severity.MEDIUM)
        ] + related)

    def reportSudoRegexp(self, domain):
        create_report([
            reporting.Title('SSSD Domain "%s": sudo rules containing wildcards '
                            'will stop working.' % domain),
            reporting.Summary('Default value of ldap_sudo_include_regexp changed '
                              'from true to false for performance reason.'),
            reporting.Groups(COMMON_REPORT_GROUPS),
            reporting.Remediation(
                hint='If you use sudo rules with wildcards, set this option to true explicitly.'
            ),
            reporting.Severity(reporting.Severity.HIGH)
        ] + related)
