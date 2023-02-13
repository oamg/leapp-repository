from leapp.libraries.common import config
from leapp.models import FstabEntry, StorageInfo
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context
from leapp.utils.report import is_inhibitor


def test_actor_with_fstab_entry(current_actor_context, monkeypatch):
    monkeypatch.setattr(config, 'get_env', lambda x, y: y)
    with_fstab_entry = [FstabEntry(fs_spec="//10.20.30.42/share1", fs_file="/mnt/win_share1",
                                   fs_vfstype="cifs",
                                   fs_mntops="credentials=/etc/win-credentials,file_mode=0755,dir_mode=0755",
                                   fs_freq="0", fs_passno="0"),
                        FstabEntry(fs_spec="//10.20.30.42/share2", fs_file="/mnt/win_share2",
                                   fs_vfstype="cifs",
                                   fs_mntops="credentials=/etc/win-credentials,file_mode=0755,dir_mode=0755",
                                   fs_freq="0", fs_passno="0"),
                        FstabEntry(fs_spec="/dev/mapper/fedora-home", fs_file="/home",
                                   fs_vfstype="ext4",
                                   fs_mntops="defaults,x-systemd.device-timeout=0",
                                   fs_freq="1", fs_passno="2")]
    current_actor_context.feed(StorageInfo(fstab=with_fstab_entry))
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)
    assert report_fields['severity'] == 'high'
    assert report_fields['title'] == "Use of CIFS detected. Upgrade can't proceed"


def test_actor_no_cifs(current_actor_context, monkeypatch):
    monkeypatch.setattr(config, 'get_env', lambda x, y: y)
    with_fstab_entry = [FstabEntry(fs_spec="/dev/mapper/fedora-home", fs_file="/home",
                                   fs_vfstype="ext4",
                                   fs_mntops="defaults,x-systemd.device-timeout=0",
                                   fs_freq="1", fs_passno="2")]
    current_actor_context.feed(StorageInfo(fstab=with_fstab_entry))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
