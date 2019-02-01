import os

from leapp.actors import Actor
from leapp.models import CheckResult, InstalledUnsignedRPM
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag


class RedHatSignedRpmCheck(Actor):
    """
    Check if there are packages not signed by Red Hat in use. If yes, warn user about it.

    If any any installed RPM package does not contain a valid signature from Red Hat, a message
    containing a warning is produced.
    """

    name = 'red_hat_signed_rpm_check'
    consumes = (InstalledUnsignedRPM,)
    produces = (CheckResult,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        skip_check = os.getenv('LEAPP_SKIP_CHECK_SIGNED_PACKAGES')
        if skip_check:
            self.produce(CheckResult(
                severity='Warning',
                result='Not Applicable',
                summary='Skipped signed packages check',
                details='Signed packages check skipped via LEAPP_SKIP_CHECK_SIGNED_PACKAGES env var'
            ))
            return

        unsigned_pkgs = next(self.consume(InstalledUnsignedRPM), InstalledUnsignedRPM())

        if len(unsigned_pkgs.items):
            # FIXME: To avoid problems during tests, this is being reported as WARNING by now
            self.produce(CheckResult(
                severity='Warning',
                result='Fail',
                summary='Packages not signed by Red Hat found in the system',
                details=('Following packages were not signed by Red Hat:\n    {}'
                         .format('\n    '.join([pkg.name for pkg in unsigned_pkgs.items]))),
                solutions=('Consider removing those packages from'
                           ' the system. Such packages could have negative impact'
                           ' on the whole upgrade process.')))
