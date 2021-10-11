import os

from leapp.libraries.actor import checkvdo
from leapp import reporting
from leapp.libraries.common.testutils import create_report_mocked


def test_no_unmigrated_vdo(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkvdo, '_canonicalize_device_path', lambda x: x)
    monkeypatch.setattr(checkvdo, '_get_blkid_vdo_results',
                        lambda: os.linesep.join([]))
    monkeypatch.setattr(checkvdo, '_get_dmsetup_vdo_results',
                        lambda: os.linesep.join([]))

    checkvdo.check_vdo()

    assert reporting.create_report.called == 1
    assert 'VDO instances that require migration: None' in reporting.create_report.report_fields['summary']


def test_unmigrated_vdo(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkvdo, '_canonicalize_device_path', lambda x: x)
    monkeypatch.setattr(checkvdo, '_get_blkid_vdo_results',
                        lambda: os.linesep.join(["/dev/sda", "/dev/sdb"]))
    monkeypatch.setattr(checkvdo, '_get_dmsetup_vdo_results',
                        lambda: os.linesep.join([]))

    checkvdo.check_vdo()

    assert reporting.create_report.called == 1
    assert 'VDO instances that require migration: None' not in reporting.create_report.report_fields['summary']
    assert 'inhibitor' in reporting.create_report.report_fields['flags']
