from leapp.actors import Actor
from leapp.libraries.actor import checkdeprecatedrpmsignature
from leapp.models import CryptoPolicyInfo, InstalledRPM, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckDeprecatedRPMSignature(Actor):
    """
    Check whether any packages signed by RSA/SHA1 are installed

    Crypto policies on RHEL 9 disallow use of the SHA-1 hash algorithm.
    Regarding the IPU, the major impact is around RPMs with RSA/SHA1 signatures
    that cannot be handled during the upgrade when SHA1 is not explicitly
    allowed (e.g. setting the LEGACY mode; which has serious impacts).

    The problem is that when rpm tries to verify the bad signature of the
    installed rpm, it ends with error regarding the new openssl policies
    (same for dnf). In such a case, rpm nor dnf prints the name of the package,
    nor report anything else useful. In case of the IPU this happens when
    the bad packages is supposed to be removed (includes upgrade, downgrade,...)
    from the system during the dnf transaction. There is no way how we could
    handle this situation from our DNF plugin (unless we disable crypto in DNF
    completely, which is not desired). Also, in case the key has not been
    imported previously, the issue will not be seen as there is no way how to
    check the signature.

    The current hotfix implementation inhibits the upgrade when any RPMs with
    RSA/SHA1 are installed on the system and:
      * the system wide crypto policy is not LEGACY or DEFAULT:SHA1
    In other cases when such RPMs are installed on the system, just report the
    high risk informing users about the situation.
    """

    name = 'check_deprecated_rpm_signature'
    consumes = (CryptoPolicyInfo, InstalledRPM)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        checkdeprecatedrpmsignature.process()
