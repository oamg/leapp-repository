from leapp.actors import Actor
from leapp.libraries.actor.grubdevname import get_grub_device
from leapp.models import GrubDevice
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class Grubdevname(Actor):
    """
    Get name of block device where GRUB is located
    """

    name = 'grubdevname'
    consumes = ()
    produces = (GrubDevice,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        get_grub_device()
