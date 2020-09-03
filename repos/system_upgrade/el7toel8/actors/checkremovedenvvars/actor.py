from leapp.actors import Actor
from leapp.libraries.actor import checkremovedenvvars
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckRemovedEnvVars(Actor):
    """
    Check for usage of removed environment variables and inhibit the upgrade
    if they are used.
    """

    name = 'check_removed_envvars'
    consumes = ()
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkremovedenvvars.process()
