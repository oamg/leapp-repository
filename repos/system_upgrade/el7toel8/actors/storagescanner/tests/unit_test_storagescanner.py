import os

from leapp import reporting
from leapp.libraries.actor import storagescanner
from leapp.libraries.common.testutils import create_report_mocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import (FstabEntry, LsblkEntry, LvdisplayEntry, MountEntry, PartitionEntry, PvsEntry,
                          SystemdMountEntry, VgsEntry, )

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def test_get_partitions_info(monkeypatch):
    def is_file_readable_mocked(path):
        return False

    expected = [
        PartitionEntry(major='252', minor='0', blocks='41943040', name='vda'),
        PartitionEntry(major='252', minor='1', blocks='1048576', name='vda1'),
        PartitionEntry(major='252', minor='2', blocks='40893440', name='vda2'),
        PartitionEntry(major='253', minor='0', blocks='39837696', name='dm-0'),
        PartitionEntry(major='253', minor='1', blocks='1048576', name='dm-1')]
    assert expected == storagescanner._get_partitions_info(os.path.join(CUR_DIR, 'files/partitions'))

    monkeypatch.setattr(storagescanner, '_is_file_readable', is_file_readable_mocked)
    assert [] == storagescanner._get_partitions_info('unreadable_file')


def test_get_fstab_info(monkeypatch):
    expected = [
        FstabEntry(
            fs_spec='/dev/mapper/rhel_ibm--p8--kvm--03--guest--02-root',
            fs_file='/',
            fs_vfstype='xfs',
            fs_mntops='defaults',
            fs_freq='0',
            fs_passno='0'),
        FstabEntry(
            fs_spec='UUID=0a5215ef-1fb4-4b1b-8860-be4baa9e624c',
            fs_file='/boot',
            fs_vfstype='xfs',
            fs_mntops='defaults',
            fs_freq='0',
            fs_passno='1'),
        FstabEntry(
            fs_spec='UUID=acf9f525-3691-429f-96d7-3f8530227062',
            fs_file='/var',
            fs_vfstype='xfs',
            fs_mntops='defaults',
            fs_freq='0',
            fs_passno='0'),
        FstabEntry(
            fs_spec='UUID=d74186c9-21d5-4549-ae26-91ca9ed36f56',
            fs_file='/tmp',
            fs_vfstype='ext4',
            fs_mntops='defaults,nodev,nosuid,noexec',
            fs_freq='1',
            fs_passno='0'),
        FstabEntry(
            fs_spec='/dev/mapper/rhel_ibm--p8--kvm--03--guest--02-swap',
            fs_file='swap',
            fs_vfstype='swap',
            fs_mntops='defaults',
            fs_freq='0',
            fs_passno='0')]
    assert expected == storagescanner._get_fstab_info(os.path.join(CUR_DIR, 'files/fstab'))
    monkeypatch.setattr(storagescanner, '_is_file_readable', lambda dummy: False)
    assert [] == storagescanner._get_fstab_info('unreadable_file')


def test_invalid_fstab_info(monkeypatch):
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    storagescanner._get_fstab_info(os.path.join(CUR_DIR, 'files/invalid_fstab'))
    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields['severity'] == 'high'
    assert 'Problems with parsing data in /etc/fstab' in reporting.create_report.report_fields['title']
    assert 'inhibitor' in reporting.create_report.report_fields['groups']
    assert any("The fstab configuration file seems to be invalid" in msg for msg in api.current_logger.errmsg)


def test_get_mount_info(monkeypatch):
    expected = [
        MountEntry(
            name='sysfs', mount='/sys', tp='sysfs',
            options='rw,seclabel,nosuid,nodev,noexec,relatime'
        ),
        MountEntry(
            name='proc', mount='/proc', tp='proc',
            options='rw,nosuid,nodev,noexec,relatime'
        ),
        MountEntry(
            name='devtmpfs', mount='/dev', tp='devtmpfs',
            options='rw,seclabel,nosuid,size=16131092k,nr_inodes=4032773,mode=755'
        ),
        MountEntry(
            name='securityfs', mount='/sys/kernel/security', tp='securityfs',
            options='rw,nosuid,nodev,noexec,relatime'
        ),
        MountEntry(
            name='tmpfs', mount='/dev/shm', tp='tmpfs',
            options='rw,seclabel,nosuid,nodev'
        ),
        MountEntry(
            name='devpts', mount='/dev/pts', tp='devpts',
            options='rw,seclabel,nosuid,noexec,relatime,gid=5,mode=620,ptmxmode=000'
        ),
        MountEntry(
            name='tmpfs', mount='/run', tp='tmpfs',
            options='rw,seclabel,nosuid,nodev,mode=755'
        ),
        MountEntry(
            name='tmpfs', mount='/sys/fs/cgroup', tp='tmpfs',
            options='ro,seclabel,nosuid,nodev,noexec,mode=755'
        ),
        MountEntry(
            name='cgroup2', mount='/sys/fs/cgroup/unified', tp='cgroup2',
            options='rw,seclabel,nosuid,nodev,noexec,relatime,nsdelegate'
        ),
        MountEntry(
            name='cgroup', mount='/sys/fs/cgroup/systemd', tp='cgroup',
            options='rw,seclabel,nosuid,nodev,noexec,relatime,xattr,name=systemd'
        ),
        MountEntry(
            name='pstore', mount='/sys/fs/pstore', tp='pstore',
            options='rw,seclabel,nosuid,nodev,noexec,relatime'
        ),
        MountEntry(
            name='bpf', mount='/sys/fs/bpf', tp='bpf',
            options='rw,nosuid,nodev,noexec,relatime,mode=700'
        ),
        MountEntry(
            name='cgroup', mount='/sys/fs/cgroup/cpuset', tp='cgroup',
            options='rw,seclabel,nosuid,nodev,noexec,relatime,cpuset'
        ),
        MountEntry(
            name='cgroup', mount='/sys/fs/cgroup/net_cls,net_prio', tp='cgroup',
            options='rw,seclabel,nosuid,nodev,noexec,relatime,net_cls,net_prio'
        ),
        MountEntry(
            name='cgroup', mount='/sys/fs/cgroup/hugetlb', tp='cgroup',
            options='rw,seclabel,nosuid,nodev,noexec,relatime,hugetlb'
        ),
        MountEntry(
            name='cgroup', mount='/sys/fs/cgroup/pids', tp='cgroup',
            options='rw,seclabel,nosuid,nodev,noexec,relatime,pids'
        ),
        MountEntry(
            name='cgroup', mount='/sys/fs/cgroup/freezer', tp='cgroup',
            options='rw,seclabel,nosuid,nodev,noexec,relatime,freezer'
        ),
        MountEntry(
            name='cgroup', mount='/sys/fs/cgroup/blkio', tp='cgroup',
            options='rw,seclabel,nosuid,nodev,noexec,relatime,blkio'
        ),
        MountEntry(
            name='cgroup', mount='/sys/fs/cgroup/devices', tp='cgroup',
            options='rw,seclabel,nosuid,nodev,noexec,relatime,devices'
        ),
        MountEntry(
            name='cgroup', mount='/sys/fs/cgroup/cpu,cpuacct', tp='cgroup',
            options='rw,seclabel,nosuid,nodev,noexec,relatime,cpu,cpuacct'
        ),
        MountEntry(
            name='cgroup', mount='/sys/fs/cgroup/memory', tp='cgroup',
            options='rw,seclabel,nosuid,nodev,noexec,relatime,memory'
        ),
        MountEntry(
            name='cgroup', mount='/sys/fs/cgroup/perf_event', tp='cgroup',
            options='rw,seclabel,nosuid,nodev,noexec,relatime,perf_event'
        ),
        MountEntry(
            name='configfs', mount='/sys/kernel/config', tp='configfs',
            options='rw,relatime'
        ),
        MountEntry(
            name='/dev/mapper/fedora-root', mount='/', tp='ext4',
            options='rw,seclabel,relatime'
        ),
        MountEntry(
            name='selinuxfs', mount='/sys/fs/selinux', tp='selinuxfs',
            options='rw,relatime'
        ),
        MountEntry(
            name='debugfs', mount='/sys/kernel/debug', tp='debugfs',
            options='rw,seclabel,relatime'
        ),
        MountEntry(
            name='hugetlbfs', mount='/dev/hugepages', tp='hugetlbfs',
            options='rw,seclabel,relatime,pagesize=2M'
        ),
        MountEntry(
            name='systemd-1', mount='/proc/sys/fs/binfmt_misc', tp='autofs',
            options='rw,relatime,fd=38,pgrp=1,timeout=0,minproto=5,maxproto=5,direct,pipe_ino=14019'
        ),
        MountEntry(
            name='mqueue', mount='/dev/mqueue', tp='mqueue',
            options='rw,seclabel,relatime'
        ),
        MountEntry(
            name='fusectl', mount='/sys/fs/fuse/connections', tp='fusectl',
            options='rw,relatime'
        ),
        MountEntry(
            name='tmpfs', mount='/tmp', tp='tmpfs',
            options='rw,seclabel,nosuid,nodev'
        ),
        MountEntry(
            name='/dev/nvme0n1p1', mount='/boot', tp='ext4',
            options='rw,seclabel,relatime'
        ),
        MountEntry(
            name='/dev/mapper/fedora-home', mount='/home', tp='ext4',
            options='rw,seclabel,relatime'
        ),
        MountEntry(
            name='sunrpc', mount='/var/lib/nfs/rpc_pipefs', tp='rpc_pipefs',
            options='rw,relatime'
        ),
        MountEntry(
            name='tmpfs', mount='/run/user/1000', tp='tmpfs',
            options='rw,seclabel,nosuid,nodev,relatime,size=3229704k,mode=700,uid=1000,gid=1000'
        ),
        MountEntry(
            name='tmpfs', mount='/run/user/42', tp='tmpfs',
            options='rw,seclabel,nosuid,nodev,relatime,size=3229704k,mode=700,uid=42,gid=42'
        ),
        MountEntry(
            name='gvfsd-fuse', mount='/run/user/1000/gvfs',
            tp='fuse.gvfsd-fuse', options='rw,nosuid,nodev,relatime,user_id=1000,group_id=1000'
        ),
        MountEntry(
            name='/dev/loop2p1', mount='/mnt/foo\\040bar', tp='iso9660',
            options='ro,nosuid,nodev,relatime,nojoliet,check=s,map=n,blocksize=2048'
        )
    ]

    assert expected == storagescanner._get_mount_info(os.path.join(CUR_DIR, 'files/mounts'))


def test_get_lsblk_info(monkeypatch):
    def get_cmd_output_mocked(cmd, delim, expected_len):
        return [
            ['vda', '252:0', '0', '40G', '0', 'disk', ''],
            ['vda1', '252:1', '0', '1G', '0', 'part', '/boot'],
            ['vda2', '252:2', '0', '39G', '0', 'part', ''],
            ['rhel_ibm--p8--kvm--03--guest--02-root', '253:0', '0', '38G', '0', 'lvm', '/'],
            ['rhel_ibm--p8--kvm--03--guest--02-swap', '253:1', '0', '1G', '0', 'lvm', '[SWAP]']]

    monkeypatch.setattr(storagescanner, '_get_cmd_output', get_cmd_output_mocked)
    expected = [
        LsblkEntry(
            name='vda',
            maj_min='252:0',
            rm='0',
            size='40G',
            ro='0',
            tp='disk',
            mountpoint=''),
        LsblkEntry(
            name='vda1',
            maj_min='252:1',
            rm='0',
            size='1G',
            ro='0',
            tp='part',
            mountpoint='/boot'),
        LsblkEntry(
            name='vda2',
            maj_min='252:2',
            rm='0',
            size='39G',
            ro='0',
            tp='part',
            mountpoint=''),
        LsblkEntry(
            name='rhel_ibm--p8--kvm--03--guest--02-root',
            maj_min='253:0',
            rm='0',
            size='38G',
            ro='0',
            tp='lvm',
            mountpoint='/'),
        LsblkEntry(
            name='rhel_ibm--p8--kvm--03--guest--02-swap',
            maj_min='253:1',
            rm='0',
            size='1G',
            ro='0',
            tp='lvm',
            mountpoint='[SWAP]')]
    assert expected == storagescanner._get_lsblk_info()


def test_get_pvs_info(monkeypatch):
    def get_cmd_output_mocked(cmd, delim, expected_len):
        return [
            ['/dev/vda2', 'rhel_ibm-p8-kvm-03-guest-02', 'lvm2', 'a--', '<39.00g', '4.00m']]

    monkeypatch.setattr(storagescanner, '_get_cmd_output', get_cmd_output_mocked)
    expected = [
        PvsEntry(
            pv='/dev/vda2',
            vg='rhel_ibm-p8-kvm-03-guest-02',
            fmt='lvm2',
            attr='a--',
            psize='<39.00g',
            pfree='4.00m')]
    assert expected == storagescanner._get_pvs_info()


def test_get_vgs_info(monkeypatch):
    def get_cmd_output_mocked(cmd, delim, expected_len):
        return [
            ['rhel_ibm-p8-kvm-03-guest-02', '1', '2', '0', 'wz--n-', '<39.00g', '4.00m']]

    monkeypatch.setattr(storagescanner, '_get_cmd_output', get_cmd_output_mocked)
    expected = [
        VgsEntry(
            vg='rhel_ibm-p8-kvm-03-guest-02',
            pv='1',
            lv='2',
            sn='0',
            attr='wz--n-',
            vsize='<39.00g',
            vfree='4.00m')]
    assert expected == storagescanner._get_vgs_info()


def test_get_lvdisplay_info(monkeypatch):
    def get_cmd_output_mocked(cmd, delim, expected_len):
        return [
            ['root', 'rhel_ibm-p8-kvm-03-guest-02', '-wi-ao----', '37.99g', '', '', '', '', '', '', '', ''],
            ['swap', 'rhel_ibm-p8-kvm-03-guest-02', '-wi-ao----', '1.00g', '', '', '', '', '', '', '', '']]

    monkeypatch.setattr(storagescanner, '_get_cmd_output', get_cmd_output_mocked)
    expected = [
        LvdisplayEntry(
            lv='root',
            vg='rhel_ibm-p8-kvm-03-guest-02',
            attr='-wi-ao----',
            lsize='37.99g',
            pool='',
            origin='',
            data='',
            meta='',
            move='',
            log='',
            cpy_sync='',
            convert=''),
        LvdisplayEntry(
            lv='swap',
            vg='rhel_ibm-p8-kvm-03-guest-02',
            attr='-wi-ao----',
            lsize='1.00g',
            pool='',
            origin='',
            data='',
            meta='',
            move='',
            log='',
            cpy_sync='',
            convert='')]
    assert expected == storagescanner._get_lvdisplay_info()


def test_get_systemd_mount_info(monkeypatch):
    def get_cmd_output_mocked(cmd, delim, expected_len):
        return [
            ['/dev/dm-1',
             'n/a',
             'n/a',
             'n/a',
             'ext4',
             'n/a',
             'bec30ca5-5403-4c23-ae6e-cb2a911bc076'],
            ['/dev/dm-3',
             'n/a',
             'n/a',
             'n/a',
             'ext4',
             'n/a',
             'd6eaf17d-e2a9-4e8d-bb54-a89c18923ea2'],
            ['/dev/sda1',
             'pci-0000:00:17.0-ata-2',
             'LITEON_LCH-256V2S',
             '0x5002303100d82b06',
             'ext4',
             'n/a',
             'c3890bf3-9273-4877-ad1f-68144e1eb858']]

    monkeypatch.setattr(storagescanner, '_get_cmd_output', get_cmd_output_mocked)
    expected = [
        SystemdMountEntry(
            node='/dev/dm-1',
            path='n/a',
            model='n/a',
            wwn='n/a',
            fs_type='ext4',
            label='n/a',
            uuid='bec30ca5-5403-4c23-ae6e-cb2a911bc076'),
        SystemdMountEntry(
            node='/dev/dm-3',
            path='n/a',
            model='n/a',
            wwn='n/a',
            fs_type='ext4',
            label='n/a',
            uuid='d6eaf17d-e2a9-4e8d-bb54-a89c18923ea2'),
        SystemdMountEntry(
            node='/dev/sda1',
            path='pci-0000:00:17.0-ata-2',
            model='LITEON_LCH-256V2S',
            wwn='0x5002303100d82b06',
            fs_type='ext4',
            label='n/a',
            uuid='c3890bf3-9273-4877-ad1f-68144e1eb858')]
    assert expected == storagescanner._get_systemd_mount_info()
