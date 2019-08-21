from leapp.libraries.actor import library
from leapp.libraries.common.testutils import create_report_mocked
from leapp import reporting


def test_uninstalled(monkeypatch):
    for config_default in (False, True):
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
        monkeypatch.setattr(library, 'is_config_default', lambda: config_default)

        library.check_chrony(False)

        assert reporting.create_report.called == 0


def test_installed_defconf(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(library, 'is_config_default', lambda: True)

    library.check_chrony(True)

    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields['title'] == 'chrony using default configuration'


def test_installed_nodefconf(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(library, 'is_config_default', lambda: False)

    library.check_chrony(True)

    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields['title'] == 'chrony using non-default configuration'
