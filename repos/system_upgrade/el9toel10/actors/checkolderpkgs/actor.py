from leapp.actors import Actor
from leapp.libraries.actor import checkolderpkgs
from leapp.models import InstalledRPM
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckOlderReleasePackages(Actor):
    """
    Check for packages from older or different RHEL releases.

    This actor detects packages with release tags that do not match the
    current system's RHEL version (e.g., .el7 or .el8 packages on a RHEL 9
    system). Such packages can cause system instability, upgrade failures,
    or result in unsupported configurations.

    When older release packages are detected, the upgrade is inhibited with
    clear remediation guidance for the user.
    """

    name = 'check_older_release_packages'
    consumes = (InstalledRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        checkolderpkgs.process()
