from leapp.actors import Actor
from leapp.libraries.actor.checkosrelease import check_os_version, skip_check
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckOSRelease(Actor):
    """
    Check if the current RHEL minor version is supported. If not, inhibit the upgrade process.

    This check can be skipped by using the LEAPP_DEVEL_SKIP_CHECK_OS_RELEASE environment variable.
    """

    name = 'check_os_release'
    consumes = ()
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if not skip_check():
            check_os_version()
