from leapp import reporting
from leapp.libraries.actor import checkchrony
from leapp.libraries.common.testutils import create_report_mocked


def test_uninstalled(monkeypatch):
    for config_default in (False, True):
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
        monkeypatch.setattr(checkchrony, 'is_config_default', lambda: config_default)

        checkchrony.check_chrony(False)

        assert reporting.create_report.called == 0


def test_installed_defconf(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkchrony, 'is_config_default', lambda: True)

    checkchrony.check_chrony(True)

    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields['title'] == 'chrony using default configuration'


def test_installed_nodefconf(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkchrony, 'is_config_default', lambda: False)

    checkchrony.check_chrony(True)

    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields['title'] == 'chrony using non-default configuration'
