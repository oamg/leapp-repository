from leapp.actors import Actor
from leapp.libraries.actor import create_iso_repofile
from leapp.models import CustomTargetRepositoryFile, TargetOSInstallationImage
from leapp.tags import IPUWorkflowTag, TargetTransactionFactsPhaseTag


class CreateISORepofile(Actor):
    """
    Create custom repofile containing information about repositories found in target OS installation ISO, if used.
    """

    name = 'create_iso_repofile'
    consumes = (TargetOSInstallationImage,)
    produces = (CustomTargetRepositoryFile,)
    tags = (IPUWorkflowTag, TargetTransactionFactsPhaseTag)

    def process(self):
        create_iso_repofile.produce_repofile_if_iso_used()
