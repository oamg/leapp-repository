from leapp.models import SSSDConfig8to9


class SSSDFactsLibrary(object):
    """
    Helper library from SSSDFacts actor to allow unit testing.
    """

    def __init__(self, config):
        self.config = config

    def get_fallback(self, section, key, fallback):
        if not self.config.has_option(section, key):
            return fallback
        return self.config.get(section, key)

    def getboolean_fallback(self, section, key, fallback):
        if not self.config.has_option(section, key):
            return fallback
        return self.config.getboolean(section, key)

    def process(self):
        """
        Check SSSD configuration for the following options:

        - sssd/enable_files_domain
        - pam/pam_cert_auth
        - explicit files provider domain present
        """
        facts = SSSDConfig8to9(
            enable_files_domain_set=False,
            explicit_files_domain=False,
            pam_cert_auth=False,
        )

        facts.enable_files_domain_set = self.config.has_option('sssd', 'enable_files_domain')
        facts.pam_cert_auth = self.getboolean_fallback('pam', 'pam_cert_auth', fallback=False)

        # Lookup domain with id_provider == files
        for section in self.config.sections():
            # Not a domain config.
            if not section.startswith('domain/'):
                continue

            # Malformed config?
            if not self.config.has_option(section, 'id_provider'):
                continue

            val = self.get_fallback(section, 'id_provider', fallback=None)
            if val == 'files':
                facts.explicit_files_domain = True
                break

        return facts
