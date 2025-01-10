from leapp.actors import Actor
from leapp.libraries.actor.distributionsignedrpmcheck import check_third_party_pkgs
from leapp.models import ThirdPartyRPM
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class DistributionSignedRpmCheck(Actor):
    """
    Check if there are any packages that are not signed by distribution GPG keys.

    We are recognizing two (three) types of packages:
    * Distribution packages - RPMs that are part of the system distribution (RHEL,
      Centos Stream, Fedora, ...) - which are recognized based on the signature
      by known GPG keys for the particular distribution.
    * Third-party packages - RPMs that are not signed by such GPG keys -
      including RPMs not signed at all. Such RPMs are considered in general as
      third party content.
    (
      * some packages are known to not be signed as they are created by
        delivered product (which can be part of the distribution). This includes
        e.g. katello RPMs created in a Satellite server. We do not report
        such packages known to us.
    )

    All such third-party installed packages are reported to inform the user to
    take care of them before, during or after the upgrade.
    """

    name = 'distribution_signed_rpm_check'
    consumes = (ThirdPartyRPM,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        check_third_party_pkgs()
