from leapp.actors import Actor
from leapp.libraries.common import persistentnetnames
from leapp.models import PersistentNetNamesFactsInitramfs
from leapp.tags import LateTestsPhaseTag, IPUWorkflowTag


class PersistentNetNamesInitramfs(Actor):
    """
    Get network interface information for physical ethernet interfaces with the new kernel in initramfs.

    This actor does exactly the same job as PersistentNetNames actor except that it runs in a later phase.
    """

    name = 'persistentnetnamesinitramfs'
    consumes = ()
    produces = (PersistentNetNamesFactsInitramfs, )
    tags = (LateTestsPhaseTag, IPUWorkflowTag)

    def process(self):
        self.produce(PersistentNetNamesFactsInitramfs(interfaces=list(persistentnetnames.interfaces())))
