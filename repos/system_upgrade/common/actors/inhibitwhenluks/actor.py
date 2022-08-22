from leapp import reporting
from leapp.actors import Actor
from leapp.models import CephInfo, StorageInfo
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class InhibitWhenLuks(Actor):
    """
    Check if any encrypted partitions is in use. If yes, inhibit the upgrade process.

    Upgrading system with encrypted partition is not supported.
    """

    name = 'check_luks_and_inhibit'
    consumes = (StorageInfo, CephInfo)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        # If encrypted Ceph volumes present, check if there are more encrypted disk in lsblk than Ceph vol
        ceph_vol = []
        try:
            ceph_info = next(self.consume(CephInfo))
            if ceph_info:
                ceph_vol = ceph_info.encrypted_volumes[:]
                for storage_info in self.consume(StorageInfo):
                    for blk in storage_info.lsblk:
                        if blk.tp == 'crypt' and blk.name not in ceph_vol:
                            create_report([
                                reporting.Title('LUKS encrypted partition detected'),
                                reporting.Summary('Upgrading system with encrypted partitions is not supported'),
                                reporting.Severity(reporting.Severity.HIGH),
                                reporting.Groups([reporting.Groups.BOOT, reporting.Groups.ENCRYPTION]),
                                reporting.Groups([reporting.Groups.INHIBITOR]),
                            ])
                            break
        except StopIteration:
            for storage_info in self.consume(StorageInfo):
                for blk in storage_info.lsblk:
                    if blk.tp == 'crypt':
                        create_report([
                            reporting.Title('LUKS encrypted partition detected'),
                            reporting.Summary('Upgrading system with encrypted partitions is not supported'),
                            reporting.Severity(reporting.Severity.HIGH),
                            reporting.Groups([reporting.Groups.BOOT, reporting.Groups.ENCRYPTION]),
                            reporting.Groups([reporting.Groups.INHIBITOR]),
                        ])
                        break
