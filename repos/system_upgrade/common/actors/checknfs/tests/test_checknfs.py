import pytest

from leapp.libraries.common import config
from leapp.models import FstabEntry, MountEntry, StorageInfo
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context
from leapp.utils.report import is_inhibitor


@pytest.mark.parametrize('nfs_fstype', ('nfs', 'nfs4'))
def test_actor_with_fstab_entry(current_actor_context, nfs_fstype, monkeypatch):
    monkeypatch.setattr(config, 'get_env', lambda x, y: y)
    with_fstab_entry = [FstabEntry(fs_spec="lithium:/mnt/data", fs_file="/mnt/data",
                                   fs_vfstype=nfs_fstype,
                                   fs_mntops="noauto,noatime,rsize=32768,wsize=32768",
                                   fs_freq="0", fs_passno="0")]
    current_actor_context.feed(StorageInfo(fstab=with_fstab_entry))
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)


def test_actor_without_fstab_entry(current_actor_context, monkeypatch):
    monkeypatch.setattr(config, 'get_env', lambda x, y: y)
    without_fstab_entry = [FstabEntry(fs_spec="/dev/mapper/fedora-home", fs_file="/home",
                                      fs_vfstype="ext4",
                                      fs_mntops="defaults,x-systemd.device-timeout=0",
                                      fs_freq="1", fs_passno="2")]
    current_actor_context.feed(StorageInfo(fstab=without_fstab_entry))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_actor_with_nfsd(current_actor_context, monkeypatch):
    monkeypatch.setattr(config, 'get_env', lambda x, y: y)
    with_nfsd = [MountEntry(name="nfsd", mount="/proc/fs/nfsd", tp="nfsd", options="rw,relatime")]
    current_actor_context.feed(StorageInfo(mount=with_nfsd))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


@pytest.mark.parametrize('nfs_fstype', ('nfs', 'nfs4'))
def test_actor_with_mount_share(current_actor_context, nfs_fstype, monkeypatch):
    monkeypatch.setattr(config, 'get_env', lambda x, y: y)
    with_mount_share = [MountEntry(name="nfs", mount="/mnt/data", tp=nfs_fstype,
                                   options="rw,nosuid,nodev,relatime,user_id=1000,group_id=1000")]
    current_actor_context.feed(StorageInfo(mount=with_mount_share))
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)


def test_actor_without_mount_share(current_actor_context, monkeypatch):
    monkeypatch.setattr(config, 'get_env', lambda x, y: y)
    without_mount_share = [MountEntry(name="tmpfs", mount="/run/snapd/ns", tp="tmpfs",
                                      options="rw,nosuid,nodev,seclabel,mode=755")]
    current_actor_context.feed(StorageInfo(mount=without_mount_share))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_actor_skipped_if_initram_network_enabled(current_actor_context, monkeypatch):
    """Check that previous inhibitors are not stopping the upgrade in case env var is set"""
    monkeypatch.setattr(config, 'get_env', lambda x, y: 'network-manager' if x == 'LEAPP_DEVEL_INITRAM_NETWORK' else y)
    with_mount_share = [MountEntry(name="nfs", mount="/mnt/data", tp='nfs',
                                   options="rw,nosuid,nodev,relatime,user_id=1000,group_id=1000")]
    with_fstab_entry = [FstabEntry(fs_spec="lithium:/mnt/data", fs_file="/mnt/data",
                                   fs_vfstype='nfs',
                                   fs_mntops="noauto,noatime,rsize=32768,wsize=32768",
                                   fs_freq="0", fs_passno="0")]
    current_actor_context.feed(StorageInfo(mount=with_mount_share,
                                           systemdmount=[],
                                           fstab=with_fstab_entry))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_actor_not_skipped_if_initram_network_empty(current_actor_context, monkeypatch):
    """Check that previous inhibitors are not stopping the upgrade in case env var is set"""
    monkeypatch.setattr(config, 'get_env', lambda x, y: '' if x == 'LEAPP_DEVEL_INITRAM_NETWORK' else y)
    with_mount_share = [MountEntry(name="nfs", mount="/mnt/data", tp='nfs',
                                   options="rw,nosuid,nodev,relatime,user_id=1000,group_id=1000")]
    with_fstab_entry = [FstabEntry(fs_spec="lithium:/mnt/data", fs_file="/mnt/data",
                                   fs_vfstype='nfs',
                                   fs_mntops="noauto,noatime,rsize=32768,wsize=32768",
                                   fs_freq="0", fs_passno="0")]
    current_actor_context.feed(StorageInfo(mount=with_mount_share,
                                           systemdmount=[],
                                           fstab=with_fstab_entry))
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)
