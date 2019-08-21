from leapp.libraries.actor import library
from leapp import reporting
from leapp.libraries.common.testutils import create_report_mocked


def test_uninstalled(monkeypatch):
    for sysconfig_default in (False, True):
        for udp_disabled in (False, True):
            monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
            monkeypatch.setattr(library, 'is_sysconfig_default', lambda: sysconfig_default)
            monkeypatch.setattr(library, 'is_udp_disabled', lambda: udp_disabled)

            library.check_memcached(False)

            assert reporting.create_report.called == 0


def test_installed_defconf(monkeypatch):
    for udp_disabled in (False, True):
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
        monkeypatch.setattr(library, 'is_sysconfig_default', lambda: True)
        monkeypatch.setattr(library, 'is_udp_disabled', lambda: udp_disabled)

        library.check_memcached(True)

        assert reporting.create_report.called == 1
        assert reporting.create_report.report_fields['title'] == 'memcached service is using default configuration'


def test_installed_nodefconf_udp(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(library, 'is_sysconfig_default', lambda: False)
    monkeypatch.setattr(library, 'is_udp_disabled', lambda: False)

    library.check_memcached(True)

    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields['title'] == 'memcached has enabled UDP port'


def test_installed_nodefconf_noudp(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(library, 'is_sysconfig_default', lambda: False)
    monkeypatch.setattr(library, 'is_udp_disabled', lambda: True)

    library.check_memcached(True)

    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields['title'] == 'memcached has already disabled UDP port'
