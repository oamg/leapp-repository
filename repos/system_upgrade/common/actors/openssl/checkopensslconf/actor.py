from leapp.actors import Actor
from leapp.libraries.actor import checkopensslconf
from leapp.models import DistributionSignedRPM, Report, TrackedFilesInfoSource
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckOpenSSLConf(Actor):
    """
    Check whether the openssl configuration and openssl-IBMCA.

    See the report messages for more details. The summary is that since RHEL 8
    it's expected to configure OpenSSL via crypto policies. Also, OpenSSL has
    different versions between major versions of RHEL:
      * RHEL 7: 1.0,
      * RHEL 8: 1.1,
      * RHEL 9: 3.0
    So OpenSSL configuration from older system does not have to be 100%
    compatible with the new system. In some cases, the old configuration could
    make the system inaccessible remotely. So new approach is to ensure the
    upgraded system will use always new default /etc/pki/tls/openssl.cnf
    configuration file (the original one will be backed up if modified by user).

    Similar for OpenSSL-IBMCA, when it's expected to configure it again on
    each newer system.
    """

    name = 'check_openssl_conf'
    consumes = (DistributionSignedRPM, TrackedFilesInfoSource)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        checkopensslconf.process()
