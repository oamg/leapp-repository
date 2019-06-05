from leapp.libraries.actor import library
from leapp.libraries.common import reporting
from leapp.libraries.common.testutils import report_generic_mocked


def test_uninstalled(monkeypatch):
    for sysconfig_default in (False, True):
        for udp_disabled in (False, True):
            monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())
            monkeypatch.setattr(library, 'is_sysconfig_default', lambda: sysconfig_default)
            monkeypatch.setattr(library, 'is_udp_disabled', lambda: udp_disabled)

            library.check_memcached(False)

            assert reporting.report_generic.called == 0


def test_installed_defconf(monkeypatch):
    for udp_disabled in (False, True):
        monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())
        monkeypatch.setattr(library, 'is_sysconfig_default', lambda: True)
        monkeypatch.setattr(library, 'is_udp_disabled', lambda: udp_disabled)

        library.check_memcached(True)

        assert reporting.report_generic.called == 1
        assert reporting.report_generic.report_fields['title'] == 'memcached service is using default configuration'


def test_installed_nodefconf_udp(monkeypatch):
    monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())
    monkeypatch.setattr(library, 'is_sysconfig_default', lambda: False)
    monkeypatch.setattr(library, 'is_udp_disabled', lambda: False)

    library.check_memcached(True)

    assert reporting.report_generic.called == 1
    assert reporting.report_generic.report_fields['title'] == 'memcached has enabled UDP port'


def test_installed_nodefconf_noudp(monkeypatch):
    monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())
    monkeypatch.setattr(library, 'is_sysconfig_default', lambda: False)
    monkeypatch.setattr(library, 'is_udp_disabled', lambda: True)

    library.check_memcached(True)

    assert reporting.report_generic.called == 1
    assert reporting.report_generic.report_fields['title'] == 'memcached has already disabled UDP port'
