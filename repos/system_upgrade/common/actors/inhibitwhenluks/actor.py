from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.common.config import get_env
from leapp.models import CephInfo, StorageInfo
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag, TargetUserSpaceUpgradeTasks


class InhibitWhenLuks(Actor):
    """
    Check if any encrypted partitions is in use. If yes, inhibit the upgrade process.

    Upgrading system with encrypted partition is not supported.
    """

    name = 'check_luks_and_inhibit'
    consumes = (StorageInfo, CephInfo)
    produces = (Report, TargetUserSpaceUpgradeTasks)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if get_env('LEAPP_DEVEL_ALLOW_DISK_ENCRYPTION', '0') == '1':
            create_report([
                reporting.Title('Experimental upgrade with encrypted disks enabled'),
                reporting.Summary(
                     'Upgrading system with encrypted partitions is not supported'
                     ' but LEAPP_DEVEL_ALLOW_DISK_ENCRYPTION=1 is set, so skip checks'
                     ' and continue with the upgrade in unsupported mode.'
                 ),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups([reporting.Groups.BOOT, reporting.Groups.ENCRYPTION]),
            ])
            required_crypt_rpms = [
                'clevis',
                'clevis-dracut',
                'clevis-systemd',
                'clevis-udisks2',
                'clevis-luks',
                'cryptsetup',
                'tpm2-tss',
                'tpm2-tools',
                'tpm2-abrmd'
            ]
            self.produce(TargetUserSpaceUpgradeTasks(install_rpms=required_pkgs))
            return
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
