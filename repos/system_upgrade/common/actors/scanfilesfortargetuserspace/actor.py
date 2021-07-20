from leapp.actors import Actor
from leapp.libraries.actor.scanfilesfortargetuserspace import scan_files_to_copy
from leapp.models import TargetUserSpacePreupgradeTasks
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanFilesForTargetUserspace(Actor):
    """
    Scan the source system and identify files that will be copied into the target userspace when it is created.
    """

    name = 'scan_files_for_target_userspace'
    consumes = ()
    produces = (TargetUserSpacePreupgradeTasks,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        scan_files_to_copy()
