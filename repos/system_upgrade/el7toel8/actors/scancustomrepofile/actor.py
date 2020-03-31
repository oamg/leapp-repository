from leapp.actors import Actor
from leapp.libraries.actor import scancustomrepofile
from leapp.models import CustomTargetRepository
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanCustomRepofile(Actor):
    """
    Scan the custom /etc/leapp/files/leapp_upgrade_repositories.repo repo file.

    This is the official path where to put the YUM/DNF repository file with
    custom repositories for the target system. These repositories will be used
    automatically for the in-place upgrade despite the enable/disable settings.

    If the file doesn't exist, nothing happens.
    """

    name = 'scan_custom_repofile'
    consumes = ()
    produces = (CustomTargetRepository,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        scancustomrepofile.process()
