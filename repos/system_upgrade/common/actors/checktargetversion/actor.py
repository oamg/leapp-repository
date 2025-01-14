from leapp.actors import Actor
from leapp.libraries.actor import checktargetversion
from leapp.models import IPUPaths
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckTargetVersion(Actor):
    """
    Check that the target system version is supported by the upgrade process.

    Invoke inhibitor if the target system is not supported.
    Allow unsupported target if `LEAPP_UNSUPPORTED=1` is set.
    """

    name = 'check_target_version'
    consumes = (IPUPaths,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checktargetversion.process()
