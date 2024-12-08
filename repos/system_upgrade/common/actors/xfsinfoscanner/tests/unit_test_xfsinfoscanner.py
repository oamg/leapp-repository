import os

from leapp.libraries.actor import xfsinfoscanner
from leapp.libraries.common.testutils import produce_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import (
    FstabEntry,
    MountEntry,
    StorageInfo,
    SystemdMountEntry,
    XFSInfo,
    XFSInfoData,
    XFSInfoFacts,
    XFSInfoLog,
    XFSInfoMetaData,
    XFSInfoNaming,
    XFSInfoRealtime,
    XFSPresence
)

TEST_XFS_INFO_FTYPE1 = """
meta-data=/dev/loop0             isize=512    agcount=4, agsize=131072 blks
         =                       sectsz=512   attr=2, projid32bit=1
         =                       crc=1        finobt=0 spinodes=0
data     =                       bsize=4096   blocks=524288, imaxpct=25
         =                       sunit=0      swidth=0 blks
naming   =version 2              bsize=4096   ascii-ci=0 ftype=1
log      =internal               bsize=4096   blocks=2560, version=2
         =                       sectsz=512   sunit=0 blks, lazy-count=1
realtime =none                   extsz=4096   blocks=0, rtextents=0
"""
TEST_XFS_INFO_FTYPE1_PARSED = {
    'meta-data': {
        'agcount': '4',
        'agsize': '131072 blks',
        'attr': '2',
        'crc': '1',
        'finobt': '0',
        'isize': '512',
        'projid32bit': '1',
        'sectsz': '512',
        'specifier': '/dev/loop0',
        'spinodes': '0'
    },
    'data': {
        'blocks': '524288',
        'bsize': '4096',
        'imaxpct': '25',
        'sunit': '0',
        'swidth': '0 blks'
    },
    'naming': {
        'ascii-ci': '0',
        'bsize': '4096',
        'ftype': '1',
        'specifier': 'version',
        'specifier_value': '2'
    },
    'log': {
        'blocks': '2560',
        'bsize': '4096',
        'lazy-count': '1',
        'sectsz': '512',
        'specifier': 'internal',
        'sunit': '0 blks',
        'version': '2'
    },
    'realtime': {
        'blocks': '0',
        'extsz': '4096',
        'rtextents': '0',
        'specifier': 'none'
    },
}
TEST_XFS_INFO_FTYPE1_MODEL = XFSInfo(
    mountpoint='/',
    meta_data=XFSInfoMetaData(device='/dev/loop0', bigtime=None, crc='1'),
    data=XFSInfoData(blocks='524288', bsize='4096'),
    naming=XFSInfoNaming(ftype='1'),
    log=XFSInfoLog(blocks='2560', bsize='4096'),
    realtime=XFSInfoRealtime()
)


TEST_XFS_INFO_FTYPE0 = """
meta-data=/dev/loop0             isize=512    agcount=4, agsize=131072 blks
         =                       sectsz=512   attr=2, projid32bit=1
         =                       crc=1        finobt=0 spinodes=0
data     =                       bsize=4096   blocks=524288, imaxpct=25
         =                       sunit=0      swidth=0 blks
naming   =version 2              bsize=4096   ascii-ci=0 ftype=0
log      =internal               bsize=4096   blocks=2560, version=2
         =                       sectsz=512   sunit=0 blks, lazy-count=1
realtime =none                   extsz=4096   blocks=0, rtextents=0
"""
TEST_XFS_INFO_FTYPE0_PARSED = {
    'meta-data': {
        'agcount': '4',
        'agsize': '131072 blks',
        'attr': '2',
        'crc': '1',
        'finobt': '0',
        'isize': '512',
        'projid32bit': '1',
        'sectsz': '512',
        'specifier': '/dev/loop0',
        'spinodes': '0'
    },
    'data': {
        'blocks': '524288',
        'bsize': '4096',
        'imaxpct': '25',
        'sunit': '0',
        'swidth': '0 blks'
    },
    'naming': {
        'ascii-ci': '0',
        'bsize': '4096',
        'ftype': '0',
        'specifier': 'version',
        'specifier_value': '2'
    },
    'log': {
        'blocks': '2560',
        'bsize': '4096',
        'lazy-count': '1',
        'sectsz': '512',
        'specifier': 'internal',
        'sunit': '0 blks',
        'version': '2'
    },
    'realtime': {
        'blocks': '0',
        'extsz': '4096',
        'rtextents': '0',
        'specifier': 'none'
    }
}
TEST_XFS_INFO_FTYPE0_MODEL = XFSInfo(
    mountpoint='/var',
    meta_data=XFSInfoMetaData(device='/dev/loop0', bigtime=None, crc='1'),
    data=XFSInfoData(blocks='524288', bsize='4096'),
    naming=XFSInfoNaming(ftype='0'),
    log=XFSInfoLog(blocks='2560', bsize='4096'),
    realtime=XFSInfoRealtime()
)


class run_mocked(object):
    def __init__(self):
        self.called = 0
        self.args = None

    def __call__(self, args, split=True):
        self.called += 1
        self.args = args

        with_ftype = {'stdout': TEST_XFS_INFO_FTYPE1.splitlines()}
        without_ftype = {'stdout': TEST_XFS_INFO_FTYPE0.splitlines()}

        if '/var' in self.args:
            return without_ftype

        return with_ftype


def test_scan_xfs_fstab(monkeypatch):
    fstab_data_no_xfs = {
        'fs_spec': '/dev/mapper/fedora-home',
        'fs_file': '/home',
        'fs_vfstype': 'ext4',
        'fs_mntops': 'defaults,x-systemd.device-timeout=0',
        'fs_freq': '1',
        'fs_passno': '2'}

    mountpoints = xfsinfoscanner.scan_xfs_fstab([FstabEntry(**fstab_data_no_xfs)])
    assert not mountpoints

    fstab_data_xfs = {
        'fs_spec': '/dev/mapper/rhel-root',
        'fs_file': '/',
        'fs_vfstype': 'xfs',
        'fs_mntops': 'defaults',
        'fs_freq': '0',
        'fs_passno': '0'}

    mountpoints = xfsinfoscanner.scan_xfs_fstab([FstabEntry(**fstab_data_xfs)])
    assert mountpoints == {'/'}


def test_scan_xfs_mount(monkeypatch):
    mount_data_no_xfs = {
        'name': 'tmpfs',
        'mount': '/run/snapd/ns',
        'tp': 'tmpfs',
        'options': 'rw,nosuid,nodev,seclabel,mode=755'}

    mountpoints = xfsinfoscanner.scan_xfs_mount([MountEntry(**mount_data_no_xfs)])
    assert not mountpoints

    mount_data_xfs = {
        'name': '/dev/vda1',
        'mount': '/boot',
        'tp': 'xfs',
        'options': 'rw,relatime,seclabel,attr2,inode64,noquota'}

    mountpoints = xfsinfoscanner.scan_xfs_mount([MountEntry(**mount_data_xfs)])
    assert mountpoints == {'/boot'}


def test_is_without_ftype(monkeypatch):
    assert xfsinfoscanner.is_without_ftype(TEST_XFS_INFO_FTYPE0_PARSED)
    assert not xfsinfoscanner.is_without_ftype(TEST_XFS_INFO_FTYPE1_PARSED)
    assert not xfsinfoscanner.is_without_ftype({'naming': {}})


def test_read_xfs_info_failed(monkeypatch):
    def _run_mocked_exception(*args, **kwargs):
        raise CalledProcessError(message='No such file or directory', command=['xfs_info', '/nosuchmountpoint'],
                                 result=1)
    # not a mountpoint
    monkeypatch.setattr(os.path, 'ismount', lambda _: False)
    monkeypatch.setattr(xfsinfoscanner, 'run', _run_mocked_exception)
    assert xfsinfoscanner.read_xfs_info('/nosuchmountpoint') is None
    # a real mountpoint but something else caused command to fail
    monkeypatch.setattr(os.path, 'ismount', lambda _: True)
    assert xfsinfoscanner.read_xfs_info('/nosuchmountpoint') is None


def test_scan_xfs_no_xfs(monkeypatch):
    monkeypatch.setattr(xfsinfoscanner, 'run', run_mocked())
    monkeypatch.setattr(os.path, 'ismount', lambda _: True)

    def consume_no_xfs_message_mocked(*models):
        yield StorageInfo()

    monkeypatch.setattr(api, 'consume', consume_no_xfs_message_mocked)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    xfsinfoscanner.scan_xfs()

    assert api.produce.called == 2
    assert len(api.produce.model_instances) == 2

    xfs_presence = next(model for model in api.produce.model_instances if isinstance(model, XFSPresence))
    assert not xfs_presence.present
    assert not xfs_presence.without_ftype
    assert not xfs_presence.mountpoints_without_ftype

    xfs_info_facts = next(model for model in api.produce.model_instances if isinstance(model, XFSInfoFacts))
    assert xfs_info_facts.mountpoints == []


def test_scan_xfs_ignored_xfs(monkeypatch):
    monkeypatch.setattr(xfsinfoscanner, 'run', run_mocked())
    monkeypatch.setattr(os.path, 'ismount', lambda _: True)

    def consume_ignored_xfs_message_mocked(*models):
        mount_data = {
            'name': '/dev/vda1',
            'mount': '/boot',
            'tp': 'xfs',
            'options': 'rw,relatime,seclabel,attr2,inode64,noquota'
        }
        yield StorageInfo(mount=[MountEntry(**mount_data)])

    monkeypatch.setattr(api, 'consume', consume_ignored_xfs_message_mocked)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    xfsinfoscanner.scan_xfs()

    assert api.produce.called == 2
    assert len(api.produce.model_instances) == 2

    xfs_presence = next(model for model in api.produce.model_instances if isinstance(model, XFSPresence))
    assert xfs_presence.present
    assert not xfs_presence.without_ftype
    assert not xfs_presence.mountpoints_without_ftype

    xfs_info_facts = next(model for model in api.produce.model_instances if isinstance(model, XFSInfoFacts))
    assert len(xfs_info_facts.mountpoints) == 1
    assert xfs_info_facts.mountpoints[0].mountpoint == '/boot'
    assert xfs_info_facts.mountpoints[0].meta_data == TEST_XFS_INFO_FTYPE1_MODEL.meta_data
    assert xfs_info_facts.mountpoints[0].data == TEST_XFS_INFO_FTYPE1_MODEL.data
    assert xfs_info_facts.mountpoints[0].naming == TEST_XFS_INFO_FTYPE1_MODEL.naming
    assert xfs_info_facts.mountpoints[0].log == TEST_XFS_INFO_FTYPE1_MODEL.log
    assert xfs_info_facts.mountpoints[0].realtime == TEST_XFS_INFO_FTYPE1_MODEL.realtime


def test_scan_xfs_with_ftype(monkeypatch):
    monkeypatch.setattr(xfsinfoscanner, 'run', run_mocked())
    monkeypatch.setattr(os.path, 'ismount', lambda _: True)

    def consume_xfs_with_ftype_message_mocked(*models):
        fstab_data = {
            'fs_spec': '/dev/mapper/rhel-root',
            'fs_file': '/',
            'fs_vfstype': 'xfs',
            'fs_mntops': 'defaults',
            'fs_freq': '0',
            'fs_passno': '0'}
        yield StorageInfo(fstab=[FstabEntry(**fstab_data)])

    monkeypatch.setattr(api, 'consume', consume_xfs_with_ftype_message_mocked)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    xfsinfoscanner.scan_xfs()

    assert api.produce.called == 2
    assert len(api.produce.model_instances) == 2

    xfs_presence = next(model for model in api.produce.model_instances if isinstance(model, XFSPresence))
    assert xfs_presence.present
    assert not xfs_presence.without_ftype
    assert not xfs_presence.mountpoints_without_ftype

    xfs_info_facts = next(model for model in api.produce.model_instances if isinstance(model, XFSInfoFacts))
    assert len(xfs_info_facts.mountpoints) == 1
    assert xfs_info_facts.mountpoints[0].mountpoint == '/'
    assert xfs_info_facts.mountpoints[0].meta_data == TEST_XFS_INFO_FTYPE1_MODEL.meta_data
    assert xfs_info_facts.mountpoints[0].data == TEST_XFS_INFO_FTYPE1_MODEL.data
    assert xfs_info_facts.mountpoints[0].naming == TEST_XFS_INFO_FTYPE1_MODEL.naming
    assert xfs_info_facts.mountpoints[0].log == TEST_XFS_INFO_FTYPE1_MODEL.log
    assert xfs_info_facts.mountpoints[0].realtime == TEST_XFS_INFO_FTYPE1_MODEL.realtime


def test_scan_xfs_without_ftype(monkeypatch):
    monkeypatch.setattr(xfsinfoscanner, 'run', run_mocked())
    monkeypatch.setattr(os.path, 'ismount', lambda _: True)

    def consume_xfs_without_ftype_message_mocked(*models):
        fstab_data = {
            'fs_spec': '/dev/mapper/rhel-root',
            'fs_file': '/var',
            'fs_vfstype': 'xfs',
            'fs_mntops': 'defaults',
            'fs_freq': '0',
            'fs_passno': '0'}
        yield StorageInfo(fstab=[FstabEntry(**fstab_data)])

    monkeypatch.setattr(api, 'consume', consume_xfs_without_ftype_message_mocked)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    xfsinfoscanner.scan_xfs()

    assert api.produce.called == 2
    assert len(api.produce.model_instances) == 2

    xfs_presence = next(model for model in api.produce.model_instances if isinstance(model, XFSPresence))
    assert xfs_presence.present
    assert xfs_presence.without_ftype
    assert xfs_presence.mountpoints_without_ftype

    xfs_info_facts = next(model for model in api.produce.model_instances if isinstance(model, XFSInfoFacts))
    assert len(xfs_info_facts.mountpoints) == 1
    assert xfs_info_facts.mountpoints[0].mountpoint == '/var'
    assert xfs_info_facts.mountpoints[0].meta_data == TEST_XFS_INFO_FTYPE0_MODEL.meta_data
    assert xfs_info_facts.mountpoints[0].data == TEST_XFS_INFO_FTYPE0_MODEL.data
    assert xfs_info_facts.mountpoints[0].naming == TEST_XFS_INFO_FTYPE0_MODEL.naming
    assert xfs_info_facts.mountpoints[0].log == TEST_XFS_INFO_FTYPE0_MODEL.log
    assert xfs_info_facts.mountpoints[0].realtime == TEST_XFS_INFO_FTYPE0_MODEL.realtime


def test_scan_xfs_no_message(monkeypatch):
    monkeypatch.setattr(xfsinfoscanner, 'run', run_mocked())
    monkeypatch.setattr(os.path, 'ismount', lambda _: True)

    def consume_no_message_mocked(*models):
        yield None

    monkeypatch.setattr(api, 'consume', consume_no_message_mocked)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    xfsinfoscanner.scan_xfs()

    assert api.produce.called == 2
    assert len(api.produce.model_instances) == 2

    xfs_presence = next(model for model in api.produce.model_instances if isinstance(model, XFSPresence))
    assert not xfs_presence.present
    assert not xfs_presence.without_ftype
    assert not xfs_presence.mountpoints_without_ftype

    xfs_info_facts = next(model for model in api.produce.model_instances if isinstance(model, XFSInfoFacts))
    assert not xfs_info_facts.mountpoints


def test_parse_xfs_info(monkeypatch):
    xfs_info = xfsinfoscanner.parse_xfs_info(TEST_XFS_INFO_FTYPE0.splitlines())
    assert xfs_info == TEST_XFS_INFO_FTYPE0_PARSED

    xfs_info = xfsinfoscanner.parse_xfs_info(TEST_XFS_INFO_FTYPE1.splitlines())
    assert xfs_info == TEST_XFS_INFO_FTYPE1_PARSED
