import os
import re


class PAM(object):
    files = [
        '/etc/pam.d/system-auth',
        '/etc/pam.d/smartcard-auth',
        '/etc/pam.d/password-auth',
        '/etc/pam.d/fingerprint-auth',
        '/etc/pam.d/postlogin'
    ]
    """
    List of system PAM configuration files.
    """

    def __init__(self, config):
        self.modules = self.parse(config)

    def parse(self, config):
        """
        Parse configuration and return list of modules that are present in the
        configuration.
        """
        result = re.findall(
            r"^[ \t]*[^#\s]+.*(pam_\S+)\.so.*$",
            config,
            re.MULTILINE
        )

        return result

    def has(self, module):
        """
        Return True if the module exist in the configuration, False otherwise.
        """
        return module in self.modules

    def has_unknown_module(self, known_modules):
        """
        Return True if the configuration has any module which is not known to
        the caller, False otherwise.
        """
        for module in self.modules:
            if module not in known_modules:
                return True

        return False

    @staticmethod
    def read_file(config):
        """
        Read file contents. Return empty string if the file does not exist.
        """
        if not os.path.isfile(config):
            return ""
        with open(config) as f:
            return f.read()

    @staticmethod
    def from_system_configuration():
        config = ""
        for f in PAM.files:
            config += PAM.read_file(f)

        return PAM(config)
