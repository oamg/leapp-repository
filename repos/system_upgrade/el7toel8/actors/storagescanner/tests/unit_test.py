from leapp.libraries.actor import library
from leapp.libraries.common import reporting
from leapp.libraries.common.testutils import report_generic_mocked
from leapp.libraries.stdlib import api
from leapp.models import PartitionEntry, FstabEntry, MountEntry, LsblkEntry, PvsEntry, VgsEntry, \
    LvdisplayEntry, SystemdMountEntry


def test_get_partitions_info(monkeypatch):
    def is_file_readable_mocked(path):
        return False

    expected = [
        PartitionEntry(major='252', minor='0', blocks='41943040', name='vda'),
        PartitionEntry(major='252', minor='1', blocks='1048576', name='vda1'),
        PartitionEntry(major='252', minor='2', blocks='40893440', name='vda2'),
        PartitionEntry(major='253', minor='0', blocks='39837696', name='dm-0'),
        PartitionEntry(major='253', minor='1', blocks='1048576', name='dm-1')]
    assert expected == library._get_partitions_info('tests/files/partitions')

    monkeypatch.setattr(library, '_is_file_readable', is_file_readable_mocked)
    assert [] == library._get_partitions_info('unreadable_file')


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
    assert expected == library._get_fstab_info('tests/files/fstab')
    monkeypatch.setattr(library, '_is_file_readable', lambda(_): False)
    assert [] == library._get_fstab_info('unreadable_file')


def test_invalid_fstab_info(monkeypatch):
    class logger_mocked(object):
        def __init__(self):
            self.errmsg = None

        def error(self, msg):
            self.errmsg = msg

        def __call__(self):
            return self

    monkeypatch.setattr(reporting, "report_with_remediation", report_generic_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    library._get_fstab_info('tests/files/invalid_fstab')
    assert reporting.report_with_remediation.called == 1
    assert reporting.report_with_remediation.report_fields['severity'] == 'high'
    assert 'Problems with parsing data in /etc/fstab' in reporting.report_with_remediation.report_fields['title']
    assert 'inhibitor' in reporting.report_with_remediation.report_fields['flags']
    assert "The fstab configuration file seems to be invalid" in api.current_logger.errmsg


def test_get_mount_info(monkeypatch):
    def get_cmd_output_mocked(cmd, delim, expected_len):
        return [
            ['sysfs', 'on', '/sys', 'type', 'sysfs', '(rw,nosuid,nodev,noexec,relatime,seclabel)'],
            ['proc', 'on', '/proc', 'type', 'proc', '(rw,nosuid,nodev,noexec,relatime)'],
            ['tmpfs', 'on', '/dev/shm', 'type', 'tmpfs', '(rw,nosuid,nodev,seclabel)'],
            ['tmpfs', 'on', '/run', 'type', 'tmpfs', '(rw,nosuid,nodev,seclabel,mode=755)']]

    monkeypatch.setattr(library, '_get_cmd_output', get_cmd_output_mocked)
    expected = [
        MountEntry(
            name='sysfs',
            mount='/sys',
            tp='sysfs',
            options='(rw,nosuid,nodev,noexec,relatime,seclabel)'),
        MountEntry(
            name='proc',
            mount='/proc',
            tp='proc',
            options='(rw,nosuid,nodev,noexec,relatime)'),
        MountEntry(
            name='tmpfs',
            mount='/dev/shm',
            tp='tmpfs',
            options='(rw,nosuid,nodev,seclabel)'),
        MountEntry(
            name='tmpfs',
            mount='/run',
            tp='tmpfs',
            options='(rw,nosuid,nodev,seclabel,mode=755)')]
    assert expected == library._get_mount_info()


def test_get_lsblk_info(monkeypatch):
    def get_cmd_output_mocked(cmd, delim, expected_len):
        return [
            ['vda', '252:0', '0', '40G', '0', 'disk', ''],
            ['vda1', '252:1', '0', '1G', '0', 'part', '/boot'],
            ['vda2', '252:2', '0', '39G', '0', 'part', ''],
            ['rhel_ibm--p8--kvm--03--guest--02-root', '253:0', '0', '38G', '0', 'lvm', '/'],
            ['rhel_ibm--p8--kvm--03--guest--02-swap', '253:1', '0', '1G', '0', 'lvm', '[SWAP]']]

    monkeypatch.setattr(library, '_get_cmd_output', get_cmd_output_mocked)
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
    assert expected == library._get_lsblk_info()


def test_get_pvs_info(monkeypatch):
    def get_cmd_output_mocked(cmd, delim, expected_len):
        return [
            ['/dev/vda2', 'rhel_ibm-p8-kvm-03-guest-02', 'lvm2', 'a--', '<39.00g', '4.00m']]

    monkeypatch.setattr(library, '_get_cmd_output', get_cmd_output_mocked)
    expected = [
        PvsEntry(
            pv='/dev/vda2',
            vg='rhel_ibm-p8-kvm-03-guest-02',
            fmt='lvm2',
            attr='a--',
            psize='<39.00g',
            pfree='4.00m')]
    assert expected == library._get_pvs_info()


def test_get_vgs_info(monkeypatch):
    def get_cmd_output_mocked(cmd, delim, expected_len):
        return [
            ['rhel_ibm-p8-kvm-03-guest-02', '1', '2', '0', 'wz--n-', '<39.00g', '4.00m']]

    monkeypatch.setattr(library, '_get_cmd_output', get_cmd_output_mocked)
    expected = [
        VgsEntry(
            vg='rhel_ibm-p8-kvm-03-guest-02',
            pv='1',
            lv='2',
            sn='0',
            attr='wz--n-',
            vsize='<39.00g',
            vfree='4.00m')]
    assert expected == library._get_vgs_info()


def test_get_lvdisplay_info(monkeypatch):
    def get_cmd_output_mocked(cmd, delim, expected_len):
        return [
            ['root', 'rhel_ibm-p8-kvm-03-guest-02', '-wi-ao----', '37.99g', '', '', '', '', '', '', '', ''],
            ['swap', 'rhel_ibm-p8-kvm-03-guest-02', '-wi-ao----', '1.00g', '', '', '', '', '', '', '', '']]

    monkeypatch.setattr(library, '_get_cmd_output', get_cmd_output_mocked)
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
    assert expected == library._get_lvdisplay_info()


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

    monkeypatch.setattr(library, '_get_cmd_output', get_cmd_output_mocked)
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
    assert expected == library._get_systemd_mount_info()
