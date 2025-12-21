from leapp.models import FstabEntry, StorageInfo
from leapp.reporting import Flags, Report, Severity
from leapp.utils.report import is_inhibitor


def test_actor_with_tmp_entry(current_actor_context):
    with_fstab_entry = [
        FstabEntry(
            fs_spec="/dev/sda2",
            fs_file="/var",
            fs_vfstype="ext4",
            fs_mntops="defaults",
            fs_freq="0",
            fs_passno="0",
        ),
        FstabEntry(
            fs_spec="/dev/sda3",
            fs_file="/tmp",
            fs_vfstype="ext4",
            fs_mntops="defaults,nodev,noexec,nosuid",
            fs_freq="0",
            fs_passno="0",
        ),
        FstabEntry(
            fs_spec="/dev/mapper/fedora-home",
            fs_file="/home",
            fs_vfstype="ext4",
            fs_mntops="defaults,x-systemd.device-timeout=0",
            fs_freq="1",
            fs_passno="2",
        ),
    ]
    current_actor_context.feed(StorageInfo(fstab=with_fstab_entry))
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)
    assert Flags.INHIBITOR in report_fields["flags"]
    assert report_fields["severity"] == Severity.HIGH
    assert report_fields["title"] == "/tmp entry detected in /etc/fstab"


def test_actor_with_tmpfs_entry(current_actor_context):
    with_fstab_entry = [
        FstabEntry(
            fs_spec="/dev/sda2",
            fs_file="/var",
            fs_vfstype="ext4",
            fs_mntops="defaults",
            fs_freq="0",
            fs_passno="0",
        ),
        FstabEntry(
            fs_spec="tmpfs",
            fs_file="/tmp",
            fs_vfstype="tmpfs",
            fs_mntops="rw,nosuid,nodev,seclabel,size=16263600k,nr_inodes=1048576,inode64",
            fs_freq="0",
            fs_passno="0",
        ),
        FstabEntry(
            fs_spec="/dev/mapper/fedora-home",
            fs_file="/home",
            fs_vfstype="ext4",
            fs_mntops="defaults,x-systemd.device-timeout=0",
            fs_freq="1",
            fs_passno="2",
        ),
    ]
    current_actor_context.feed(StorageInfo(fstab=with_fstab_entry))
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)
    assert Flags.INHIBITOR in report_fields["flags"]
    assert report_fields["severity"] == Severity.HIGH
    assert report_fields["title"] == "/tmp entry detected in /etc/fstab"


def test_actor_with_no_tmp_entry(current_actor_context):
    with_fstab_entry = [
        FstabEntry(
            fs_spec="/dev/mapper/fedora-home",
            fs_file="/home",
            fs_vfstype="ext4",
            fs_mntops="defaults,x-systemd.device-timeout=0",
            fs_freq="1",
            fs_passno="2",
        )
    ]
    current_actor_context.feed(StorageInfo(fstab=with_fstab_entry))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
