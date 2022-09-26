from leapp.models import (
    IfCfg,
    IfCfgProperty,
    NetworkManagerConnection,
    NetworkManagerConnectionProperty,
    NetworkManagerConnectionSetting
)
from leapp.reporting import Report
from leapp.utils.report import is_inhibitor


def test_no_conf(current_actor_context):
    """
    No report if there are no networks.
    """

    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_no_wireless(current_actor_context):
    """
    No report if there's a keyfile, but it's not for a wireless connection.
    """

    not_wifi_nm_conn = NetworkManagerConnection(filename='/NM/wlan0.nmconn', settings=(
        NetworkManagerConnectionSetting(name='connection'),
    ))

    current_actor_context.feed(not_wifi_nm_conn)
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_keyfile_static_wep(current_actor_context):
    """
    Report if there's a static WEP keyfile.
    """

    static_wep_nm_conn = NetworkManagerConnection(filename='/NM/wlan0.nmconn', settings=(
        NetworkManagerConnectionSetting(name='wifi-security', properties=(
            NetworkManagerConnectionProperty(name='auth-alg', value='open'),
            NetworkManagerConnectionProperty(name='key-mgmt', value='none'),
            NetworkManagerConnectionProperty(name='wep-key-type', value='1'),
        )),
    ))

    current_actor_context.feed(static_wep_nm_conn)
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)


def test_keyfile_dynamic_wep(current_actor_context):
    """
    Report if there's a dynamic WEP keyfile.
    """

    dynamic_wep_conn = NetworkManagerConnection(filename='/NM/wlan0.nmconn', settings=(
        NetworkManagerConnectionSetting(name='wifi-security', properties=(
            NetworkManagerConnectionProperty(name='key-mgmt', value='ieee8021x'),
        )),
    ))

    current_actor_context.feed(dynamic_wep_conn)
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)


def test_ifcfg_static_wep_ask(current_actor_context):
    """
    Report if there's a static WEP sysconfig without stored key.
    """

    static_wep_ask_key_ifcfg = IfCfg(filename='/NM/ifcfg-wlan0', properties=(
        IfCfgProperty(name='TYPE', value='Wireless'),
        IfCfgProperty(name='ESSID', value='wep1'),
        IfCfgProperty(name='NAME', value='wep1'),
        IfCfgProperty(name='MODE', value='Managed'),
        IfCfgProperty(name='WEP_KEY_FLAGS', value='ask'),
        IfCfgProperty(name='SECURITYMODE', value='open'),
        IfCfgProperty(name='DEFAULTKEY', value='1'),
        IfCfgProperty(name='KEY_TYPE', value='key'),
    ))

    current_actor_context.feed(static_wep_ask_key_ifcfg)
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)


def test_ifcfg_static_wep(current_actor_context):
    """
    Report if there's a static WEP sysconfig with a stored passphrase.
    """

    static_wep_ifcfg = IfCfg(filename='/NM/ifcfg-wlan0', secrets=(
        IfCfgProperty(name='KEY_PASSPHRASE1', value=None),
    ))

    current_actor_context.feed(static_wep_ifcfg)
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)


def test_ifcfg_dynamic_wep(current_actor_context):
    """
    Report if there's a dynamic WEP sysconfig.
    """

    dynamic_wep_ifcfg = IfCfg(filename='/NM/ifcfg-wlan0', properties=(
        IfCfgProperty(name='ESSID', value='dynwep1'),
        IfCfgProperty(name='MODE', value='Managed'),
        IfCfgProperty(name='KEY_MGMT', value='IEEE8021X'),
        IfCfgProperty(name='TYPE', value='Wireless'),
        IfCfgProperty(name='NAME', value='dynwep1'),
    ))

    current_actor_context.feed(dynamic_wep_ifcfg)
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)
