import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import library
from leapp.libraries.stdlib import api
from leapp.models import StorageInfo, FstabEntry, MountEntry, XFSPresence


class call_mocked(object):
    def __init__(self):
        self.called = 0

    def __call__(self, args, split=True):
        self.called += 1
        self.args = args

        with_ftype = [
            "meta-data=/dev/loop0             isize=512    agcount=4, agsize=131072 blks",
            "         =                       sectsz=512   attr=2, projid32bit=1",
            "         =                       crc=1        finobt=0 spinodes=0",
            "data     =                       bsize=4096   blocks=524288, imaxpct=25",
            "         =                       sunit=0      swidth=0 blks",
            "naming   =version 2              bsize=4096   ascii-ci=0 ftype=1",
            "log      =internal               bsize=4096   blocks=2560, version=2",
            "         =                       sectsz=512   sunit=0 blks, lazy-count=1",
            "realtime =none                   extsz=4096   blocks=0, rtextents=0"]

        without_ftype = [
            "meta-data=/dev/loop0             isize=512    agcount=4, agsize=131072 blks",
            "         =                       sectsz=512   attr=2, projid32bit=1",
            "         =                       crc=1        finobt=0 spinodes=0",
            "data     =                       bsize=4096   blocks=524288, imaxpct=25",
            "         =                       sunit=0      swidth=0 blks",
            "naming   =version 2              bsize=4096   ascii-ci=0 ftype=0",
            "log      =internal               bsize=4096   blocks=2560, version=2",
            "         =                       sectsz=512   sunit=0 blks, lazy-count=1",
            "realtime =none                   extsz=4096   blocks=0, rtextents=0"]

        if "/var" in self.args:
            return without_ftype

        return with_ftype


class produce_mocked(object):
    def __init__(self):
        self.called = 0

    def __call__(self, *model_instances):
        self.called += 1
        self.model_instances = model_instances


def test_check_xfs_fstab(monkeypatch):
    fstab_data_no_xfs = {
        "fs_spec": "/dev/mapper/fedora-home",
        "fs_file": "/home",
        "fs_vfstype": "ext4",
        "fs_mntops": "defaults,x-systemd.device-timeout=0",
        "fs_freq": "1",
        "fs_passno": "2"}

    mountpoints = library.check_xfs_fstab([FstabEntry(**fstab_data_no_xfs)])
    assert len(mountpoints) == 0

    fstab_data_xfs = {
        "fs_spec": "/dev/mapper/rhel-root",
        "fs_file": "/",
        "fs_vfstype": "xfs",
        "fs_mntops": "defaults",
        "fs_freq": "0",
        "fs_passno": "0"}

    mountpoints = library.check_xfs_fstab([FstabEntry(**fstab_data_xfs)])
    assert mountpoints == {"/"}


def test_check_xfs_mount(monkeypatch):
    mount_data_no_xfs = {
        "name": "tmpfs",
        "mount": "/run/snapd/ns",
        "tp": "tmpfs",
        "options": "rw,nosuid,nodev,seclabel,mode=755"}

    mountpoints = library.check_xfs_mount([MountEntry(**mount_data_no_xfs)])
    assert len(mountpoints) == 0

    mount_data_xfs = {
        "name": "/dev/vda1",
        "mount": "/boot",
        "tp": "xfs",
        "options": "rw,relatime,seclabel,attr2,inode64,noquota"}

    mountpoints = library.check_xfs_mount([MountEntry(**mount_data_xfs)])
    assert mountpoints == {"/boot"}


def test_is_xfs_without_ftype(monkeypatch):
    monkeypatch.setattr(library, "call", call_mocked())

    assert library.is_xfs_without_ftype("/var")
    assert ' '.join(library.call.args) == "/usr/sbin/xfs_info /var"

    assert not library.is_xfs_without_ftype("/boot")
    assert ' '.join(library.call.args) == "/usr/sbin/xfs_info /boot"


def test_check_xfs(monkeypatch):
    monkeypatch.setattr(library, "call", call_mocked())
    monkeypatch.setattr(api, "produce", produce_mocked())

    def consume_no_xfs_message_mocked(*models):
        yield StorageInfo()
    monkeypatch.setattr(api, "consume", consume_no_xfs_message_mocked)

    library.check_xfs()
    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1
    assert type(api.produce.model_instances[0]) is XFSPresence
    assert not api.produce.model_instances[0].present
    assert not api.produce.model_instances[0].without_ftype

    api.produce.called = 0

    def consume_ignored_xfs_message_mocked(*models):
        mount_data = {
            "name": "/dev/vda1",
            "mount": "/boot",
            "tp": "xfs",
            "options": "rw,relatime,seclabel,attr2,inode64,noquota"}
        yield StorageInfo(mount=[MountEntry(**mount_data)])
    monkeypatch.setattr(api, "consume", consume_ignored_xfs_message_mocked)

    library.check_xfs()
    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1
    assert type(api.produce.model_instances[0]) is XFSPresence
    assert not api.produce.model_instances[0].present
    assert not api.produce.model_instances[0].without_ftype

    api.produce.called = 0

    def consume_xfs_with_ftype_message_mocked(*models):
        fstab_data = {
            "fs_spec": "/dev/mapper/rhel-root",
            "fs_file": "/",
            "fs_vfstype": "xfs",
            "fs_mntops": "defaults",
            "fs_freq": "0",
            "fs_passno": "0"}
        yield StorageInfo(fstab=[FstabEntry(**fstab_data)])
    monkeypatch.setattr(api, "consume", consume_xfs_with_ftype_message_mocked)

    library.check_xfs()
    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1
    assert type(api.produce.model_instances[0]) is XFSPresence
    assert api.produce.model_instances[0].present
    assert not api.produce.model_instances[0].without_ftype

    api.produce.called = 0

    def consume_xfs_without_ftype_message_mocked(*models):
        fstab_data = {
            "fs_spec": "/dev/mapper/rhel-root",
            "fs_file": "/var",
            "fs_vfstype": "xfs",
            "fs_mntops": "defaults",
            "fs_freq": "0",
            "fs_passno": "0"}
        yield StorageInfo(fstab=[FstabEntry(**fstab_data)])
    monkeypatch.setattr(api, "consume", consume_xfs_without_ftype_message_mocked)

    library.check_xfs()
    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1
    assert type(api.produce.model_instances[0]) is XFSPresence
    assert api.produce.model_instances[0].present
    assert api.produce.model_instances[0].without_ftype

    def consume_no_message_mocked(*models):
        yield None
    monkeypatch.setattr(api, "consume", consume_no_message_mocked)

    with pytest.raises(StopActorExecutionError):
        library.check_xfs()
