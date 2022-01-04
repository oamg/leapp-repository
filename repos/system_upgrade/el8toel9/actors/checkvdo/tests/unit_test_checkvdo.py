import os

from leapp import reporting
from leapp.libraries.actor import checkvdo
from leapp.libraries.common.testutils import create_report_mocked


def _patch_checkvdo_noop_unmigrated_vdo(monkeypatch):
    monkeypatch.setattr(checkvdo, '_check_for_unmigrated_vdo_devices', lambda: None)


def _patch_checkvdo_noop_migration_failed_vdo(monkeypatch):
    monkeypatch.setattr(checkvdo, '_check_for_migration_failed_vdo_devices', lambda: None)


def test_no_unmigrated_vdo(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkvdo, '_canonicalize_device_path', lambda x: x)

    monkeypatch.setattr(checkvdo, '_get_unmigrated_vdo_blkid_results',
                        lambda: os.linesep.join([]))

    _patch_checkvdo_noop_migration_failed_vdo(monkeypatch)

    monkeypatch.setattr(checkvdo, '_required_packages_not_installed', lambda: [])
    checkvdo.check_vdo()

    assert reporting.create_report.called == 1
    assert 'VDO devices that require migration: None' in reporting.create_report.report_fields['summary']


def test_unmigrated_vdo(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkvdo, '_canonicalize_device_path', lambda x: x)

    monkeypatch.setattr(checkvdo, '_get_unmigrated_vdo_blkid_results',
                        lambda: os.linesep.join(['/dev/sda', '/dev/sdb']))

    _patch_checkvdo_noop_migration_failed_vdo(monkeypatch)

    monkeypatch.setattr(checkvdo, '_required_packages_not_installed', lambda: [])
    checkvdo.check_vdo()

    assert reporting.create_report.called == 1
    assert 'VDO devices that require migration: None' not in reporting.create_report.report_fields['summary']
    assert '/dev/sda' in reporting.create_report.report_fields['summary']
    assert '/dev/sdb' in reporting.create_report.report_fields['summary']
    assert 'inhibitor' in reporting.create_report.report_fields['flags']


def test_no_migration_failed_vdo(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkvdo, '_canonicalize_device_path', lambda x: x)

    _patch_checkvdo_noop_unmigrated_vdo(monkeypatch)

    monkeypatch.setattr(checkvdo, '_get_migration_failed_lsblk_results',
                        lambda: os.linesep.join(['/dev/sda disk',
                                                 '/dev/sdb disk',
                                                 '/dev/sdc disk',
                                                 '/dev/sr0 rom']))
    monkeypatch.setattr(checkvdo, '_get_migration_failed_blkid_results',
                        lambda: os.linesep.join(['/dev/sda', '/dev/sdb']))
    monkeypatch.setattr(checkvdo, '_is_post_migration_vdo_device', lambda _: False)

    monkeypatch.setattr(checkvdo, '_required_packages_not_installed', lambda: [])
    checkvdo.check_vdo()

    assert reporting.create_report.called == 0


def test_migration_failed_vdo_before_lvm(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkvdo, '_canonicalize_device_path', lambda x: x)

    _patch_checkvdo_noop_unmigrated_vdo(monkeypatch)

    monkeypatch.setattr(checkvdo, '_get_migration_failed_lsblk_results',
                        lambda: os.linesep.join(['/dev/sda disk',
                                                 '/dev/sdb disk',
                                                 '/dev/sdc disk',
                                                 '/dev/sr0 rom']))
    monkeypatch.setattr(checkvdo, '_get_migration_failed_blkid_results',
                        lambda: os.linesep.join(['/dev/sda', '/dev/sdb']))
    monkeypatch.setattr(checkvdo, '_is_post_migration_vdo_device', lambda _: True)

    monkeypatch.setattr(checkvdo, '_required_packages_not_installed', lambda: [])
    checkvdo.check_vdo()

    assert reporting.create_report.called == 1
    assert 'VDO devices that did not complete migration:' in reporting.create_report.report_fields['summary']
    assert '/dev/sda' not in reporting.create_report.report_fields['summary']
    assert '/dev/sdb' not in reporting.create_report.report_fields['summary']
    assert '/dev/sdc' in reporting.create_report.report_fields['summary']


def test_no_vdo_package_installed(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    monkeypatch.setattr(checkvdo, '_required_packages_not_installed', lambda: ['vdo'])
    checkvdo.check_vdo()

    assert reporting.create_report.called == 1
    assert 'package(s) required for upgrade validation check' in reporting.create_report.report_fields['summary']
    assert 'inhibitor' in reporting.create_report.report_fields['flags']
