from leapp.actors import Actor
from leapp.libraries.actor.authselectscanner import (
    Authconfig,
    AuthselectScannerLibrary,
    DConf,
    read_file
)
from leapp.libraries.common.pam import PAM
from leapp.models import Authselect
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class AuthselectScanner(Actor):
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

    name = 'authselect_scanner'
    consumes = ()
    produces = (Authselect,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    known_modules = [
        'pam_access',
        'pam_deny',
        'pam_ecryptfs',
        'pam_env',
        'pam_faildelay',
        'pam_faillock',
        'pam_fprintd',
        'pam_keyinit',
        'pam_krb5',
        'pam_lastlog',
        'pam_limits',
        'pam_localuser',
        'pam_mkhomedir',
        'pam_oddjob_mkhomedir',
        'pam_permit',
        'pam_pkcs11',
        'pam_pwquality',
        'pam_sss',
        'pam_succeed_if',
        'pam_systemd',
        'pam_u2f',
        'pam_umask',
        'pam_unix',
        'pam_winbind'
    ]
    """
    List of PAM modules that are known by authselect.
    """

    def process(self):
        # Load configuration
        ac = Authconfig(read_file('/etc/sysconfig/authconfig'))
        dconf = DConf(read_file('/etc/dconf/db/distro.d/10-authconfig'))
        pam = PAM.from_system_configuration()
        nsswitch = read_file("/etc/nsswitch.conf")

        scanner = AuthselectScannerLibrary(
            self.known_modules,
            ac, dconf, pam, nsswitch
        )

        self.produce(scanner.process())
