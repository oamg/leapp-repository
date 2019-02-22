import os

from leapp.actors import Actor
from leapp.models import InstalledUnsignedRPM
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag
from leapp.reporting import Report
from leapp.libraries.common.reporting import report_generic, report_with_remediation

class RedHatSignedRpmCheck(Actor):
    """
    Check if there are packages not signed by Red Hat in use. If yes, warn user about it.

    If any any installed RPM package does not contain a valid signature from Red Hat, a message
    containing a warning is produced.
    """

    name = 'red_hat_signed_rpm_check'
    consumes = (InstalledUnsignedRPM,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        skip_check = os.getenv('LEAPP_SKIP_CHECK_SIGNED_PACKAGES')
        if skip_check:
            report_generic(title='Skipped signed packages check', 
                           severity='low',
                           summary='Signed packages check skipped via LEAPP_SKIP_CHECK_SIGNED_PACKAGES env var')
            return

        unsigned_pkgs = next(self.consume(InstalledUnsignedRPM), InstalledUnsignedRPM())

        if len(unsigned_pkgs.items):
            unsigned_packages_new_line = '\n'.join([pkg.name for pkg in unsigned_pkgs.items])
            unsigned_packages = ' '.join([pkg.name for pkg in unsigned_pkgs.items])
            remediation = 'yum remove {}'.format(unsigned_packages)
            report_with_remediation(
                title='Packages not signed by Red Hat found in the system',
                summary='Following packages were not signed by Red Hat:\n    {}.'.format(unsigned_packages_new_line),
                remediation=remediation,
                severity='high',
                )
