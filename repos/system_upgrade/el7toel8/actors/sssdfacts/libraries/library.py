from leapp.models import SSSDConfig, SSSDDomainConfig


class SSSDFactsLibrary(object):
    """
    Helper library from SSSDFacts actor to allow unit testing.
    """
    def __init__(self, config):
        self.config = config

    def process(self):
        """
        Check SSSD configuration for changes in RHEL8 and return them in SSSDConfig
        model.

        These changes are:
        - id_provider=local is no longer supported and will be ignored
        - ldap_groups_use_matching_rule_in_chain was removed and will be ignored
        - ldap_initgroups_use_matching_rule_in_chain was removed and will be ignored
        - ldap_sudo_include_regexp changed default from true to false
        """
        facts = SSSDConfig(domains=[])

        for section in self.config.sections():
            # We are interested only in domains.
            if not section.startswith('domain/'):
                continue

            domain = SSSDDomainConfig(
                name=section[len('domain/'):],
                options=[]
            )

            steps = {
                'local_provider': self.checkLocalProvider(domain.name),
                'groups_chain': self.checkRemovedOption(
                    domain.name, 'ldap_groups_use_matching_rule_in_chain'
                ),
                'initgroups_chain': self.checkRemovedOption(
                    domain.name, 'ldap_initgroups_use_matching_rule_in_chain'
                ),
                'sudo_regexp': self.checkSudoRegexp(domain.name)
            }

            for key, value in steps.items():
                if value:
                    domain.options.append(key)

            facts.domains.append(domain)

        return facts

    def checkLocalProvider(self, domain):
        """
        Check if any id_provider=local is configured.
        """
        provider = self.get_provider(domain, 'id_provider')
        if provider != 'local':
            return False

        return True

    def checkRemovedOption(self, domain, option):
        """
        Check if specific option that has been removed is present.
        """
        section = self.get_domain_section(domain)
        if not self.config.has_option(section, option):
            return False

        return True

    def checkSudoRegexp(self, domain):
        """
        Check if ldap_sudo_include_regexp is not set explicitly.
        """
        section = self.get_domain_section(domain)
        provider = self.get_provider(domain, 'sudo_provider', ['id_provider'])

        if provider not in ['ad', 'ldap']:
            return False

        if self.config.has_option(section, 'ldap_sudo_include_regexp'):
            return False

        return True

    def get_domain_section(self, domain):
        """
        Convert domain name to ini format section.
        """
        return 'domain/' + domain

    def get_provider(self, domain, provider, fallbacks=None):
        """
        Return configured provider.
        """
        providers = [provider] + (fallbacks if fallbacks else [])

        section = self.get_domain_section(domain)
        for option in providers:
            if self.config.has_option(section, option):
                return self.config.get(section, option)

        return None
