from leapp.actors import Actor
from leapp.models import Inhibitor, StorageInfo
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class InhibitWhenLuks(Actor):
    name = 'check_luks_and_inhibit'
    description = 'Inhibit upgrade process if encrypted partition is detected'
    consumes = (StorageInfo,)
    produces = (Inhibitor,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        for storage_info in self.consume(StorageInfo):
            for blk in storage_info.lsblk:
                if blk.tp == 'crypt':
                    self.produce(Inhibitor(
                        summary='LUKS encrypted partition detected',
                        details='Upgrading system with encrypted partitions is not supported',
                        solutions='If the encrypted partition is not system one and the system '
                                  'is not depending on it, you can remove/blacklist it from '
                                  'the system'))
                    break
