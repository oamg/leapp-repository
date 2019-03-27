from leapp.snactor.fixture import current_actor_context
from leapp.models import StorageInfo, FstabEntry, MountEntry
from leapp.reporting import Report


def test_actor_with_fstab_entry(current_actor_context):
    with_fstab_entry = [FstabEntry(fs_spec="lithium:/mnt/data", fs_file="/mnt/data",
                                   fs_vfstype="nfs",
                                   fs_mntops="noauto,noatime,rsize=32768,wsize=32768",
                                   fs_freq="0", fs_passno="0")]
    current_actor_context.feed(StorageInfo(fstab=with_fstab_entry))
    current_actor_context.run()
    assert 'inhibitor' in current_actor_context.consume(Report)[0].flags


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
    assert 'inhibitor' in current_actor_context.consume(Report)[0].flags


def test_actor_without_mount_share(current_actor_context):
    without_mount_share = [MountEntry(name="tmpfs", mount="/run/snapd/ns", tp="tmpfs",
                                      options="rw,nosuid,nodev,seclabel,mode=755")]
    current_actor_context.feed(StorageInfo(mount=without_mount_share))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
