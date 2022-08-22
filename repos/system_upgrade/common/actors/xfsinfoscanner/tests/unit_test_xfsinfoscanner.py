from leapp.libraries.actor import xfsinfoscanner
from leapp.libraries.common.testutils import produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import FstabEntry, MountEntry, StorageInfo, SystemdMountEntry, XFSPresence


class run_mocked(object):
    def __init__(self):
        self.called = 0
        self.args = None

    def __call__(self, args, split=True):
        self.called += 1
        self.args = args

        with_ftype = {'stdout': [
            "meta-data=/dev/loop0             isize=512    agcount=4, agsize=131072 blks",
            "         =                       sectsz=512   attr=2, projid32bit=1",
            "         =                       crc=1        finobt=0 spinodes=0",
            "data     =                       bsize=4096   blocks=524288, imaxpct=25",
            "         =                       sunit=0      swidth=0 blks",
            "naming   =version 2              bsize=4096   ascii-ci=0 ftype=1",
            "log      =internal               bsize=4096   blocks=2560, version=2",
            "         =                       sectsz=512   sunit=0 blks, lazy-count=1",
            "realtime =none                   extsz=4096   blocks=0, rtextents=0"]}

        without_ftype = {'stdout': [
            "meta-data=/dev/loop0             isize=512    agcount=4, agsize=131072 blks",
            "         =                       sectsz=512   attr=2, projid32bit=1",
            "         =                       crc=1        finobt=0 spinodes=0",
            "data     =                       bsize=4096   blocks=524288, imaxpct=25",
            "         =                       sunit=0      swidth=0 blks",
            "naming   =version 2              bsize=4096   ascii-ci=0 ftype=0",
            "log      =internal               bsize=4096   blocks=2560, version=2",
            "         =                       sectsz=512   sunit=0 blks, lazy-count=1",
            "realtime =none                   extsz=4096   blocks=0, rtextents=0"]}

        if "/var" in self.args:
            return without_ftype

        return with_ftype


def test_scan_xfs_fstab(monkeypatch):
    fstab_data_no_xfs = {
        "fs_spec": "/dev/mapper/fedora-home",
        "fs_file": "/home",
        "fs_vfstype": "ext4",
        "fs_mntops": "defaults,x-systemd.device-timeout=0",
        "fs_freq": "1",
        "fs_passno": "2"}

    mountpoints = xfsinfoscanner.scan_xfs_fstab([FstabEntry(**fstab_data_no_xfs)])
    assert not mountpoints

    fstab_data_xfs = {
        "fs_spec": "/dev/mapper/rhel-root",
        "fs_file": "/",
        "fs_vfstype": "xfs",
        "fs_mntops": "defaults",
        "fs_freq": "0",
        "fs_passno": "0"}

    mountpoints = xfsinfoscanner.scan_xfs_fstab([FstabEntry(**fstab_data_xfs)])
    assert mountpoints == {"/"}


def test_scan_xfs_mount(monkeypatch):
    mount_data_no_xfs = {
        "name": "tmpfs",
        "mount": "/run/snapd/ns",
        "tp": "tmpfs",
        "options": "rw,nosuid,nodev,seclabel,mode=755"}

    mountpoints = xfsinfoscanner.scan_xfs_mount([MountEntry(**mount_data_no_xfs)])
    assert not mountpoints

    mount_data_xfs = {
        "name": "/dev/vda1",
        "mount": "/boot",
        "tp": "xfs",
        "options": "rw,relatime,seclabel,attr2,inode64,noquota"}

    mountpoints = xfsinfoscanner.scan_xfs_mount([MountEntry(**mount_data_xfs)])
    assert mountpoints == {"/boot"}


def test_is_xfs_without_ftype(monkeypatch):
    monkeypatch.setattr(xfsinfoscanner, "run", run_mocked())

    assert xfsinfoscanner.is_xfs_without_ftype("/var")
    assert ' '.join(xfsinfoscanner.run.args) == "/usr/sbin/xfs_info /var"

    assert not xfsinfoscanner.is_xfs_without_ftype("/boot")
    assert ' '.join(xfsinfoscanner.run.args) == "/usr/sbin/xfs_info /boot"


def test_scan_xfs(monkeypatch):
    monkeypatch.setattr(xfsinfoscanner, "run", run_mocked())

    def consume_no_xfs_message_mocked(*models):
        yield StorageInfo()

    monkeypatch.setattr(api, "consume", consume_no_xfs_message_mocked)
    monkeypatch.setattr(api, "produce", produce_mocked())

    xfsinfoscanner.scan_xfs()
    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1
    assert isinstance(api.produce.model_instances[0], XFSPresence)
    assert not api.produce.model_instances[0].present
    assert not api.produce.model_instances[0].without_ftype
    assert not api.produce.model_instances[0].mountpoints_without_ftype

    def consume_ignored_xfs_message_mocked(*models):
        mount_data = {
            "name": "/dev/vda1",
            "mount": "/boot",
            "tp": "xfs",
            "options": "rw,relatime,seclabel,attr2,inode64,noquota"}
        yield StorageInfo(mount=[MountEntry(**mount_data)])

    monkeypatch.setattr(api, "consume", consume_ignored_xfs_message_mocked)
    monkeypatch.setattr(api, "produce", produce_mocked())

    xfsinfoscanner.scan_xfs()
    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1
    assert isinstance(api.produce.model_instances[0], XFSPresence)
    assert api.produce.model_instances[0].present
    assert not api.produce.model_instances[0].without_ftype
    assert not api.produce.model_instances[0].mountpoints_without_ftype

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
    monkeypatch.setattr(api, "produce", produce_mocked())

    xfsinfoscanner.scan_xfs()
    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1
    assert isinstance(api.produce.model_instances[0], XFSPresence)
    assert api.produce.model_instances[0].present
    assert not api.produce.model_instances[0].without_ftype
    assert not api.produce.model_instances[0].mountpoints_without_ftype

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
    monkeypatch.setattr(api, "produce", produce_mocked())

    xfsinfoscanner.scan_xfs()
    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1
    assert isinstance(api.produce.model_instances[0], XFSPresence)
    assert api.produce.model_instances[0].present
    assert api.produce.model_instances[0].without_ftype
    assert api.produce.model_instances[0].mountpoints_without_ftype
    assert len(api.produce.model_instances[0].mountpoints_without_ftype) == 1
    assert api.produce.model_instances[0].mountpoints_without_ftype[0] == '/var'

    def consume_no_message_mocked(*models):
        yield None

    monkeypatch.setattr(api, "consume", consume_no_message_mocked)
    monkeypatch.setattr(api, "produce", produce_mocked())

    xfsinfoscanner.scan_xfs()
    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1
    assert isinstance(api.produce.model_instances[0], XFSPresence)
    assert not api.produce.model_instances[0].present
    assert not api.produce.model_instances[0].without_ftype
    assert not api.produce.model_instances[0].mountpoints_without_ftype
