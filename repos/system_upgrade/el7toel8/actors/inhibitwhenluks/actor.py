from leapp.actors import Actor
from leapp.models import StorageInfo
from leapp.reporting import Report, create_report
from leapp import reporting
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
                    create_report([
                        reporting.Title('LUKS encrypted partition detected'),
                        reporting.Summary('Upgrading system with encrypted partitions is not supported'),
                        reporting.Severity(reporting.Severity.HIGH),
                        reporting.Groups([reporting.Groups.BOOT,
                                          reporting.Groups.ENCRYPTION,
                                          reporting.Groups.INHIBITOR]),
                    ])
                    break
