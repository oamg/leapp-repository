import platform

from leapp.actors import Actor
from leapp.libraries.actor.grubdevname import get_grub_device
from leapp.libraries.common.config import architecture
from leapp.libraries.common.utils import skip_actor_execution_if
from leapp.models import GrubDevice
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


@skip_actor_execution_if(platform.machine() == architecture.ARCH_S390X)
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
