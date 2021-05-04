from leapp.actors import Actor
from leapp.libraries.actor.biosdevname import check_biosdevname
from leapp.models import KernelCmdlineArg, PersistentNetNamesFacts
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class Biosdevname(Actor):
    """
    Enable biosdevname on the target RHEL system if all interfaces on the source RHEL
    system use biosdevname naming scheme and if machine vendor is DELL
    """

    name = 'biosdevname'
    consumes = (PersistentNetNamesFacts,)
    produces = (KernelCmdlineArg,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        check_biosdevname()
