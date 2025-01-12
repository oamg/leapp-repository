from leapp.actors import Actor
from leapp.libraries.actor.distributionsignedrpmcheck import check_unsigned_packages
from leapp.models import InstalledUnsignedRPM
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class DistributionSignedRpmCheck(Actor):
    """
    Check if there are any packages that are not signed by distribution GPG keys.

    We are recognizing two (three) types of packages:
    * RPMs that are part of the system distribution (RHEL, Centos Stream,
      Fedora, ...) - which are recognized based on the signature by known GPG
      keys for the particular distribution.
    * RPMs that are not signed by such GPG keys - including RPMs not signed
      at all. Such RPMs are considered in general as third party content.
    (
      * some packages are known to not be signed as they are created by
        delivered product (which can be part of the distribution). This includes
        e.g. katello RPMs created in a Satellite server. We do not report
        such packages known to us.
    )

    If any such non-distribution installed RPMs are detected, report it
    to inform that user needs to take care about them before/during/after
    the upgrade.
    """

    name = 'distribution_signed_rpm_check'
    consumes = (InstalledUnsignedRPM,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        check_unsigned_packages()
