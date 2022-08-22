from leapp.actors import Actor
from leapp.libraries.actor import checketcreleasever
from leapp.models import PkgManagerInfo, Report, RHUIInfo
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckEtcReleasever(Actor):
    """
    Check releasever info and provide a guidance based on the facts
    """

    name = 'check_etc_releasever'
    consumes = (PkgManagerInfo, RHUIInfo)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checketcreleasever.process()
