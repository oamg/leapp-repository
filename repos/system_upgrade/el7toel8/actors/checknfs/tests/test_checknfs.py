from leapp.snactor.fixture import current_actor_context
from leapp.models import StorageInfo, SystemdMountEntry, FstabEntry, MountEntry
from leapp.reporting import Report


def test_actor_with_systemdmount_entry(current_actor_context):
    with_systemdmount_entry = [SystemdMountEntry(node="nfs", path="n/a", model="n/a",
                                                 wwn="n/a", fs_type="nfs", label="n/a",
                                                 uuid="n/a")]
    current_actor_context.feed(StorageInfo(systemdmount=with_systemdmount_entry))
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report
    assert 'inhibitor' in report_fields['groups']


def test_actor_without_systemdmount_entry(current_actor_context):
    without_systemdmount_entry = [SystemdMountEntry(node="/dev/sda1",
                                                    path="pci-0000:00:17.0-ata-2",
                                                    model="TOSHIBA_THNSNJ512GDNU_A",
                                                    wwn="0x500080d9108e8753",
                                                    fs_type="ext4", label="n/a",
                                                    uuid="5675d309-eff7-4eb1-9c27-58bc5880ec72")]
    current_actor_context.feed(StorageInfo(systemdmount=without_systemdmount_entry))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_actor_with_fstab_entry(current_actor_context):
    with_fstab_entry = [FstabEntry(fs_spec="lithium:/mnt/data", fs_file="/mnt/data",
                                   fs_vfstype="nfs",
                                   fs_mntops="noauto,noatime,rsize=32768,wsize=32768",
                                   fs_freq="0", fs_passno="0")]
    current_actor_context.feed(StorageInfo(fstab=with_fstab_entry))
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report
    assert 'inhibitor' in report_fields['groups']


def test_actor_without_fstab_entry(current_actor_context):
    without_fstab_entry = [FstabEntry(fs_spec="/dev/mapper/fedora-home", fs_file="/home",
                                      fs_vfstype="ext4",
                                      fs_mntops="defaults,x-systemd.device-timeout=0",
                                      fs_freq="1", fs_passno="2")]
    current_actor_context.feed(StorageInfo(fstab=without_fstab_entry))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_actor_with_mount_share(current_actor_context):
    with_mount_share = [MountEntry(name="nfs", mount="/mnt/data", tp="nfs",
                                   options="rw,nosuid,nodev,relatime,user_id=1000,group_id=1000")]
    current_actor_context.feed(StorageInfo(mount=with_mount_share))
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report
    assert 'inhibitor' in report_fields['groups']


def test_actor_without_mount_share(current_actor_context):
    without_mount_share = [MountEntry(name="tmpfs", mount="/run/snapd/ns", tp="tmpfs",
                                      options="rw,nosuid,nodev,seclabel,mode=755")]
    current_actor_context.feed(StorageInfo(mount=without_mount_share))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
