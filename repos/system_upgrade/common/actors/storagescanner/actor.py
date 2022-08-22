from leapp.actors import Actor
from leapp.libraries.actor import storagescanner
from leapp.models import StorageInfo
from leapp.reporting import Report
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class StorageScanner(Actor):
    """
    Provides data about storage settings.

    After collecting data from tools like mount, lsblk, pvs, vgs and lvdisplay, and relevant files
    under /proc/partitions and /etc/fstab, a message with relevant data will be produced.
    """

    name = 'storage_scanner'
    consumes = ()
    produces = (Report, StorageInfo)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        self.produce(storagescanner.get_storage_info())
