from leapp.actors import Actor
from leapp.libraries.actor import scanblacklistca
from leapp.models import BlackListCA, BlackListError
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanBlackListCA(Actor):
    """
    Scan the file system for distrusted CA's in the blacklist directory.

    The will be moved to the corresponding blocklist directory as the blacklist
    directory is deprecated in RHEL-9
    """

    name = 'scanblacklistca'
    consumes = ()
    produces = (BlackListCA, BlackListError)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scanblacklistca.process()
