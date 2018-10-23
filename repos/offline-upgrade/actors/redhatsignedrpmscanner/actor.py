import os

from leapp.actors import Actor
from leapp.models import CheckResult, InstalledRedHatSignedRPM, InstalledRPM, RPM
from leapp.tags import IPUWorkflowTag, FactsPhaseTag

class RedHatSignedRpmScanner(Actor):
    name = 'red_hat_signed_rpm_scanner'
    description = 'Scan from installed RPM packages those that were signed by Red Hat.'
    consumes = (InstalledRPM,)
    produces = (CheckResult, InstalledRedHatSignedRPM,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        skip_check = os.getenv('LEAPP_SKIP_CHECK_SIGNED_PACKAGES')

        RH_SIGS = ['199e2f91fd431d51',
                   '5326810137017186',
                   '938a80caf21541eb',
                   'fd372689897da07a',
                   '45689c882fa658e0']

        # FIXME: Skip Leapp packages since they are not yet signed
        WHITELIST_PKGS = ['leapp',
                          'leapp-repository',
                          'python2-leapp',
                          'snactor']

        signed_pkgs = InstalledRedHatSignedRPM()
        unsigned_pkgs = []

        for rpm_pkgs in self.consume(InstalledRPM):
            if skip_check:
                signed_pkgs.items.extend(rpm_pkgs.items)
                continue

            for pkg in rpm_pkgs.items:
                if any(key in pkg.pgpsig for key in RH_SIGS):
                    signed_pkgs.items.append(pkg)
                else:
                    if any(name in pkg.name for name in WHITELIST_PKGS):
                        continue

                    unsigned_pkgs.append(pkg.name)

        if not skip_check and unsigned_pkgs:
            self.produce(CheckResult(
                severity='Error',
                result='Fail',
                summary='Packages not signed by Red Hat found in the system',
                details='Following packages not signed by Red Hat were found in the system: ' + (',').join(unsigned_pkgs),
                solutions='Remove not signed by Red Hat packages from the system'
            ))
            return

        if skip_check:
            self.produce(CheckResult(
                severity='Warning',
                result='Not Applicable',
                summary='Skipped signed packages check',
                details='Signed packages check skipped via LEAPP_SKIP_CHECK_SIGNED_PACKAGES env var'
            ))

        self.produce(signed_pkgs)
