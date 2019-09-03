from leapp.actors import Actor
from leapp.libraries.actor.library import check_os_version, skip_check
from leapp.libraries.common.config import version
from leapp.models import OSReleaseFacts
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckOSRelease(Actor):
    """
    Check if a supported release version of system's OS is in use. If not, inhibit upgrade process.

    Based on OS release collected facts, this actor will compare current release with supported
    versions. If a problem is found an inhibition message will be generated. This check can be
    skipped by using LEAPP_SKIP_CHECK_OS_RELEASE environment variable.
    """

    name = 'check_os_release'
    consumes = (OSReleaseFacts,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if not skip_check():
            check_os_version(version.SUPPORTED_VERSION)
