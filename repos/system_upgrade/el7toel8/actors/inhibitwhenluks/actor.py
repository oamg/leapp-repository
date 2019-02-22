from leapp.actors import Actor
from leapp.models import StorageInfo
from leapp.reporting import Report
from leapp.libraries.common.reporting import report_with_remediation
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class InhibitWhenLuks(Actor):
    """
    Check if any encrypted partitions is in use. If yes, inhibit the upgrade process.

    Upgrading system with encrypted partition is not supported.
    """

    name = 'check_luks_and_inhibit'
    consumes = (StorageInfo,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        for storage_info in self.consume(StorageInfo):
            for blk in storage_info.lsblk:
                if blk.tp == 'crypt':
                    report_with_remediation(
                        title='LUKS encrypted partition detected',
                        summary='Upgrading system with encrypted partitions is not supported',
                        remediation='If the encrypted partition is not system one and the system '
                                    'is not depending on it, you can remove/blacklist it from '
                                    'the system',
                        severity='high',
                        flags=['inhibitor'])
                    break
