from leapp.actors import Actor
from leapp.libraries.actor import removeupgradeartifacts
from leapp.tags import InterimPreparationPhaseTag, IPUWorkflowTag


class RemoveUpgradeArtifacts(Actor):
    """
    Removes artifacts left over by previous leapp runs

    After the upgrade process, there might be some leftover files, which need
    to be cleaned up before running another upgrade.

    Removed artifacts:
    - /root/tmp_leapp_py3/ directory (includes ".leapp_upgrade_failed" flag file)
    """

    name = 'remove_upgrade_artifacts'
    consumes = ()
    produces = ()
    tags = (InterimPreparationPhaseTag, IPUWorkflowTag)

    def process(self):
        removeupgradeartifacts.process()
