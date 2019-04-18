from leapp.actors import Actor
from leapp.libraries.common.reporting import report_generic, report_with_remediation
from leapp.models import SSSDConfig
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag


class SSSDCheck(Actor):
    '''
    Check SSSD configuration for changes in RHEL8 and report them.

    These changes are:
    - id_provider=local is no longer supported and will be ignored
    - ldap_groups_use_matching_rule_in_chain was removed and will be ignored
    - ldap_initgroups_use_matching_rule_in_chain was removed and will be ignored
    - ldap_sudo_include_regexp changed default from true to false
    '''

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
        report_generic(
            title='SSSD Domain "%s": local provider is no longer '
                  'supported and the domain will be ignored.' % domain,
            summary='Local provider is no longer supported.'
        )

    def reportRemovedOption(self, domain, option):
        report_generic(
            title='SSSD Domain "%s": option %s has no longer '
                  'any effect' % (domain, option),
            summary='Option %s was removed and it will be ignored.' % option
        )

    def reportSudoRegexp(self, domain):
        report_with_remediation(
            title='SSSD Domain "%s": sudo rules containing wildcards '
                  'will stop working.' % domain,
            summary='Default value of ldap_sudo_include_regexp changed '
                    'from true to false for performance reason.',
            remediation='If you use sudo rules with wildcards, set this option '
                        'to true explicitly.'
        )
