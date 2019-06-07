from leapp.libraries.actor import library
from leapp.libraries.common import reporting
from leapp.libraries.common.testutils import report_generic_mocked


def test_uninstalled(monkeypatch):
    for config_default in (False, True):
        monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())
        monkeypatch.setattr(library, 'is_config_default', lambda: config_default)

        library.check_chrony(False)

        assert reporting.report_generic.called == 0


def test_installed_defconf(monkeypatch):
    monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())
    monkeypatch.setattr(library, 'is_config_default', lambda: True)

    library.check_chrony(True)

    assert reporting.report_generic.called == 1
    assert reporting.report_generic.report_fields['title'] == 'chrony using default configuration'


def test_installed_nodefconf(monkeypatch):
    monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())
    monkeypatch.setattr(library, 'is_config_default', lambda: False)

    library.check_chrony(True)

    assert reporting.report_generic.called == 1
    assert reporting.report_generic.report_fields['title'] == 'chrony using non-default configuration'
