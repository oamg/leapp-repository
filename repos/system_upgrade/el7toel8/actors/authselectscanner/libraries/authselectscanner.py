import os
import re
import textwrap

from six import StringIO

from leapp.libraries.common import utils
from leapp.libraries.stdlib import CalledProcessError, run
from leapp.models import Authselect


def read_file(config):
    """
        Read file contents. Return empty string if the file does not exist.
    """
    if not os.path.isfile(config):
        return ""
    with open(config) as f:
        return f.read()


def is_service_enabled(service):
    """
        Return true if @service is enabled with systemd, false otherwise.
    """
    try:
        run(["/usr/bin/systemctl", "is-enabled", "{}.service".format(service)])
    except (OSError, CalledProcessError):
        return False

    return True


class ConfigFile(object):
    """
        Base class for config parsers.
    """

    def __init__(self, content):
        parser = utils.parse_config(StringIO(textwrap.dedent(content)))
        self.config = parser

    def get_string(self, section, option):
        if not self.config.has_option(section, option):
            return None

        return self.config.get(section, option).strip('"\'')

    def get_bool(self, section, option):
        if not self.config.has_option(section, option):
            return False

        return self.config.getboolean(section, option)


class Authconfig(ConfigFile):
    """
        Parse authconfig configuration.
    """

    def __init__(self, config):
        # We add a custom section to convert the config to ini format
        super(Authconfig, self).__init__('[authconfig]\n' + config)

    def get_string(self, option):
        return super(Authconfig, self).get_string('authconfig', option)

    def get_bool(self, option):
        return super(Authconfig, self).get_bool('authconfig', option)


class DConf(ConfigFile):
    """
        Parse dconf configuration.
    """


class AuthselectScannerLibrary(object):
    """
    Detect what authselect configuration should be suggested to administrator.

    1. Detect possible authselect profile by looking up modules in PAM
       or by checking that daemon is enabled.
       - pam_sss -> sssd
       - pam_winbind -> winbind
       - ypbind enabled -> nis

       If more then one module/daemon is detected that we will keep the
       configuration intact. No authselect profile can be applied.

    2. Detect authselect profile features by looking up modules in PAM
       or nsswitch.conf.
       - pam_faillock => with-faillock
       - pam_fprintd => with-fingerprint
       - pam_access => with-pamaccess
       - pam_mkhomedir => with-mkhomedir
       - pam_oddjob_mkhomedir => with-mkhomedir

    3. Check if there are any unknown PAM modules.
       If there are used PAM modules not used in authselect (such as pam_ldap),
       we must keep the configuration intact.

    4. Check if authconfig was used to create current configuration.
       If yes, we can automatically convert the configuration to authselect.
       If no, we need admin's confirmation.

       - Check that /etc/sysconfig/authconfig exists.
       - Check that PAM configuration uses authconfig files.
       - Check that PAM configuration was not touch after sysconfig file
         was created.
    """

    def __init__(self, known_modules, authconfig, dconf, pam, nsswitch):
        self.known_modules = known_modules
        self.ac = authconfig
        self.dconf = dconf
        self.pam = pam
        self.nsswitch = nsswitch

        self.profile = None
        self.features = []
        self.confirm = True

    def process(self):
        # Detect possible authselect configuration
        self.profile = self.step_detect_profile()
        self.features += self.step_detect_features()
        self.features += self.step_detect_sssd_features(self.profile)
        self.features += self.step_detect_winbind_features(self.profile)

        # Check if there is any module that is not known by authselect.
        # In this case we must left existing configuration intact.
        if self.pam.has_unknown_module(self.known_modules):
            self.profile = None
            self.features = []

        # Check if the proposed authselect configuration can be activated
        # automatically or admin's confirmation is required.
        self.confirm = self.step_detect_if_confirmation_is_required()

        # Remove duplicates
        self.features = sorted(set(self.features))

        return Authselect(
            profile=self.profile,
            features=self.features,
            confirm=self.confirm
        )

    def step_detect_profile(self):
        """
        Authselect supports three different profiles:
          - sssd
          - winbind
          - nis

        Only one of these profiles can be selected therefore if existing
        configuration contains combination of these daemons we can not
        suggest any profile and must keep existing configuration.
        """
        enabled_no = 0
        profile = None

        if self.pam.has('pam_sss'):
            profile = 'sssd'
            enabled_no += 1

        if self.pam.has('pam_winbind'):
            profile = 'winbind'
            enabled_no += 1

        if is_service_enabled('ypbind'):
            profile = 'nis'
            enabled_no += 1

        return profile if enabled_no == 1 else None

    def step_detect_features(self):
        pam_map = {
            'pam_faillock': 'with-faillock',
            'pam_fprintd': 'with-fingerprint',
            'pam_access': 'with-pamaccess',
            'pam_mkhomedir': 'with-mkhomedir',
            'pam_oddjob_mkhomedir': 'with-mkhomedir'
        }

        features = []

        for module, feature in pam_map.items():
            if self.pam.has(module):
                features.append(feature)

        return features

    def step_detect_sssd_features(self, profile):
        if profile != "sssd":
            return []

        # sudoers: sss
        result = re.search(
            "^[ \t]*sudoers[ \t]*:.*sss.*$",
            self.nsswitch,
            re.MULTILINE
        )

        features = []

        if result is not None:
            features.append("with-sudo")

        # SSSD Smartcard support
        # We enable smartcard support only if it was not handled by pam_pkcs11.
        # Otherwise pam_pkcs11 configuration must be converted manually.
        if not self.pam.has('pam_pkcs11'):
            if self.ac.get_bool('USESMARTCARD'):
                features.append("with-smartcard")

            if self.ac.get_bool('FORCESMARTCARD'):
                features.append("with-smartcard-required")

            if self.dconf.get_string(
                    'org/gnome/settings-daemon/peripherals/smartcard',
                    'removal-action'
            ) == 'lock-screen':
                features.append("with-smartcard-lock-on-removal")

        return features

    def step_detect_winbind_features(self, profile):
        if profile != "winbind":
            return []

        if self.ac.get_bool('WINBINDKRB5'):
            return ['with-krb5']

        return []

    def step_detect_if_confirmation_is_required(self):
        sysconfig = '/etc/sysconfig/authconfig'
        links = {
            '/etc/pam.d/fingerprint-auth': '/etc/pam.d/fingerprint-auth-ac',
            '/etc/pam.d/password-auth': '/etc/pam.d/password-auth-ac',
            '/etc/pam.d/postlogin': '/etc/pam.d/postlogin-ac',
            '/etc/pam.d/smartcard-auth': '/etc/pam.d/smartcard-auth-ac',
            '/etc/pam.d/system-auth': '/etc/pam.d/system-auth-ac'
        }

        # Check that authconfig was used to create the configuration
        if not os.path.isfile(sysconfig):
            return True

        # Check that all files are symbolic links to authconfig files
        for name, target in links.items():
            if not os.path.islink(name):
                return True

            if os.readlink(name) != target:
                return True

        # Check that all file were not modified after
        # /etc/sysconfig/authconfig was created.
        mtime = os.path.getmtime(sysconfig)
        for f in links.values():
            if os.path.getmtime(f) > mtime:
                return True

        return False
