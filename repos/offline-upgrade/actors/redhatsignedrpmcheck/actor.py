import os

from leapp.actors import Actor
from leapp.models import CheckResult, InstalledUnsignedRPM, RPM
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag

class RedHatSignedRpmCheck(Actor):
    name = 'red_hat_signed_rpm_check'
    description = 'Notify about unsupported RPM packages not signed by Red Hat.'
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
            self.produce(CheckResult(
                severity='Error',
                result='Fail',
                summary='Packages not signed by Red Hat found in the system',
                details='Following packages not signed by Red Hat were found in the system:\n' + ('\n').join(unsigned_pkgs),
                solutions='Remove not signed by Red Hat packages from the system'
            ))
