from leapp.actors import Actor
from leapp.libraries.actor import distributionsignedrpmscanner
from leapp.models import DistributionSignedRPM, InstalledRedHatSignedRPM, InstalledRPM, InstalledUnsignedRPM
from leapp.tags import FactsPhaseTag, IPUWorkflowTag
from leapp.utils.deprecation import suppress_deprecation


@suppress_deprecation(InstalledRedHatSignedRPM)
class DistributionSignedRpmScanner(Actor):
    """
    Provide data about distribution signed & unsigned RPM packages.

    For various checks and actions done during the upgrade it's important to
    know what packages are signed by GPG keys of the installed linux system
    distribution. RPMs that are not provided in the distribution could have
    different versions, different behaviour, and also it could be completely
    different application just with the same RPM name.

    For that reasons, various actors rely on the DistributionSignedRPM message
    to check whether particular package is installed, to be sure it provides
    valid data. Fingerprints of distribution GPG keys are stored under
      common/files/distro/<distro>/gpg_signatures.json
    where <distro> is distribution ID of the installed system (e.g. centos, rhel).

    If the file for the installed distribution is not find, end with error.
    """

    name = 'distribution_signed_rpm_scanner'
    consumes = (InstalledRPM,)
    produces = (DistributionSignedRPM, InstalledRedHatSignedRPM, InstalledUnsignedRPM,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        distributionsignedrpmscanner.process()
