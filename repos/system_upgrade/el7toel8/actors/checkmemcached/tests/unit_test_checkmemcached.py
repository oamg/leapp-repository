from leapp import reporting
from leapp.libraries.actor import checkmemcached
from leapp.libraries.common.testutils import create_report_mocked


def test_uninstalled(monkeypatch):
    for sysconfig_default in (False, True):
        for udp_disabled in (False, True):
            monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
            monkeypatch.setattr(checkmemcached, 'is_sysconfig_default', lambda: sysconfig_default, )
            monkeypatch.setattr(checkmemcached, 'is_udp_disabled', lambda: udp_disabled)

            checkmemcached.check_memcached(False)

            assert reporting.create_report.called == 0


def test_installed_defconf(monkeypatch):
    for udp_disabled in (False, True):
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
        monkeypatch.setattr(checkmemcached, 'is_sysconfig_default', lambda: True)
        monkeypatch.setattr(checkmemcached, 'is_udp_disabled', lambda: udp_disabled)

        checkmemcached.check_memcached(True)

        assert reporting.create_report.called == 1
        assert reporting.create_report.report_fields['title'] == 'memcached service is using default configuration'


def test_installed_nodefconf_udp(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkmemcached, 'is_sysconfig_default', lambda: False)
    monkeypatch.setattr(checkmemcached, 'is_udp_disabled', lambda: False)

    checkmemcached.check_memcached(True)

    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields['title'] == 'memcached has enabled UDP port'


def test_installed_nodefconf_noudp(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkmemcached, 'is_sysconfig_default', lambda: False)
    monkeypatch.setattr(checkmemcached, 'is_udp_disabled', lambda: True)

    checkmemcached.check_memcached(True)

    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields['title'] == 'memcached has already disabled UDP port'
