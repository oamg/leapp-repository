from leapp.actors import Actor
from leapp.libraries.actor import checkblacklistca
from leapp.models import BlackListCA, BlackListError, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckBlackListCA(Actor):
    """
    No documentation has been provided for the checkblacklistca actor.
    """

    name = 'checkblacklistca'
    consumes = (BlackListCA, BlackListError)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkblacklistca.process()
