import pytest

from leapp import reporting
from leapp.libraries.actor import checkstratis
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import FstabEntry, StorageInfo
from leapp.utils.report import is_inhibitor

_NON_STRATIS_ENTRY = FstabEntry(
    fs_spec='/dev/mapper/rhel-home',
    fs_file='/home',
    fs_vfstype='xfs',
    fs_mntops='defaults',
    fs_freq='1',
    fs_passno='2',
)

# Stratis filesystem referenced by its symlink under /dev/stratis/
_STRATIS_DEVICE_ENTRY = FstabEntry(
    fs_spec='/dev/stratis/mypool/myfs',
    fs_file='/mnt/stratis_dev',
    fs_vfstype='xfs',
    fs_mntops='defaults,x-systemd.requires=stratisd-min.service',
    fs_freq='0',
    fs_passno='0',
)

# Stratis filesystem referenced by UUID, recognisable only by the mount options
_STRATIS_UUID_ENTRY = FstabEntry(
    fs_spec='UUID=8d0dbd4e-4b8a-4b8a-9c1e-3b3a1d6f5c2a',
    fs_file='/mnt/stratis_uuid',
    fs_vfstype='xfs',
    fs_mntops=('defaults,x-systemd.requires=stratis-fstab-setup@1234abcd-1234-abcd-1234-abcd1234abcd.service'
               ',x-systemd.after=stratis-fstab-setup@1234abcd-1234-abcd-1234-abcd1234abcd.service'),
    fs_freq='0',
    fs_passno='0',
)


@pytest.mark.parametrize(
    ('entry', 'expected'),
    [
        (_NON_STRATIS_ENTRY, False),
        (_STRATIS_DEVICE_ENTRY, True),
        (_STRATIS_UUID_ENTRY, True),
    ]
)
def test_is_stratis_entry(entry, expected):
    assert checkstratis._is_stratis_entry(entry) == expected


def test_no_report_without_stratis(monkeypatch):
    logger = logger_mocked()
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=[StorageInfo(fstab=[_NON_STRATIS_ENTRY])]))

    checkstratis.process()

    assert not reporting.create_report.called
    assert 'No Stratis filesystem detected in /etc/fstab.' in logger.dbgmsg


def test_no_report_with_empty_fstab(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[StorageInfo(fstab=[])]))

    checkstratis.process()

    assert not reporting.create_report.called


def test_inhibits_when_stratis_in_fstab(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[
        StorageInfo(fstab=[_NON_STRATIS_ENTRY, _STRATIS_DEVICE_ENTRY, _STRATIS_UUID_ENTRY])
    ]))

    checkstratis.process()

    assert reporting.create_report.called == 1
    report = reporting.create_report.reports[0]
    assert is_inhibitor(report)
    assert report['severity'] == reporting.Severity.HIGH
    assert report['title'] == 'Use of Stratis detected. Upgrade cannot proceed'
    assert '/mnt/stratis_dev' in report['summary']
    assert '/mnt/stratis_uuid' in report['summary']
    assert '/home' not in report['summary']
