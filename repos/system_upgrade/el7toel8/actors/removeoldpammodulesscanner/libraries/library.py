from leapp.models import RemovedPAMModules


class RemoveOldPAMModulesScannerLibrary(object):
    """
    Scan PAM configuration for modules that are not available in RHEL-8.

    PAM module pam_krb5 and pam_pkcs11 are no longer present in RHEL-8
    and must be removed from PAM configuration, otherwise it may lock out
    the system.
    """

    def __init__(self, pam):
        self.pam = pam

    def process(self):
        # PAM modules pam_pkcs11 and pam_krb5 are no longer available in
        # RHEL8. We must remove them because if they are left in PAM
        # configuration it may lock out the system.
        modules = []
        for module in ['pam_krb5', 'pam_pkcs11']:
            if self.pam.has(module):
                modules.append(module)

        return RemovedPAMModules(
            modules=modules
        )
