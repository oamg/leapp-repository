from leapp.actors import Actor
from leapp.libraries.actor.checkvdo import check_vdo
from leapp.models import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckVdo(Actor):
    """
    Check if vdo devices need to be migrated to lvm management.
    """

    name = 'check_vdo'
    consumes = ()
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        self.produce(check_vdo())
