import errno
import textwrap

import mock
import six

from leapp import reporting
from leapp.libraries.actor import networkdeprecations
from leapp.libraries.common.testutils import create_report_mocked, make_OSError


def _listdir_nm_conn(path):
    if path == networkdeprecations.NM_CONN_DIR:
        return ['connection']
    raise make_OSError(errno.ENOENT)


def _listdir_ifcfg(path):
    if path == networkdeprecations.SYSCONFIG_DIR:
        return ['ifcfg-wireless']
    raise make_OSError(errno.ENOENT)


def _listdir_keys(path):
    if path == networkdeprecations.SYSCONFIG_DIR:
        return ['keys-wireless']
    raise make_OSError(errno.ENOENT)


def test_no_conf(monkeypatch):
    """
    No report if there are no networks.
    """

    monkeypatch.setattr(networkdeprecations.os, 'listdir', lambda _: ())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    networkdeprecations.process()
    assert not reporting.create_report.called


def test_no_wireless(monkeypatch):
    """
    No report if there's a keyfile, but it's not for a wireless connection.
    """

    mock_config = mock.mock_open(read_data='[connection]')
    with mock.patch('builtins.open' if six.PY3 else '__builtin__.open', mock_config):
        monkeypatch.setattr(networkdeprecations.os, 'listdir', _listdir_nm_conn)
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
        networkdeprecations.process()
        assert not reporting.create_report.called


def test_keyfile_static_wep(monkeypatch):
    """
    Report if there's a static WEP keyfile.
    """

    STATIC_WEP_CONN = textwrap.dedent("""
        [wifi-security]
        auth-alg=open
        key-mgmt=none
        wep-key-type=1
        wep-key0=abcde
    """)

    mock_config = mock.mock_open(read_data=STATIC_WEP_CONN)
    with mock.patch('builtins.open' if six.PY3 else '__builtin__.open', mock_config):
        monkeypatch.setattr(networkdeprecations.os, 'listdir', _listdir_nm_conn)
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
        networkdeprecations.process()
        assert reporting.create_report.called


def test_keyfile_dynamic_wep(monkeypatch):
    """
    Report if there's a dynamic WEP keyfile.
    """

    DYNAMIC_WEP_CONN = textwrap.dedent("""
        [wifi-security]
        key-mgmt=ieee8021x
    """)

    mock_config = mock.mock_open(read_data=DYNAMIC_WEP_CONN)
    with mock.patch('builtins.open' if six.PY3 else '__builtin__.open', mock_config):
        monkeypatch.setattr(networkdeprecations.os, 'listdir', _listdir_nm_conn)
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
        networkdeprecations.process()
        assert reporting.create_report.called


def test_ifcfg_static_wep_ask(monkeypatch):
    """
    Report if there's a static WEP sysconfig without stored key.
    """

    STATIC_WEP_ASK_KEY_SYSCONFIG = textwrap.dedent("""
        TYPE=Wireless
        ESSID=wep1
        NAME=wep1
        MODE=Managed
        WEP_KEY_FLAGS=ask
        SECURITYMODE=open
        DEFAULTKEY=1
        KEY_TYPE=key
    """)

    mock_config = mock.mock_open(read_data=STATIC_WEP_ASK_KEY_SYSCONFIG)
    with mock.patch('builtins.open' if six.PY3 else '__builtin__.open', mock_config):
        monkeypatch.setattr(networkdeprecations.os, 'listdir', _listdir_ifcfg)
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
        networkdeprecations.process()
        assert reporting.create_report.called


def test_ifcfg_static_wep(monkeypatch):
    """
    Report if there's a static WEP sysconfig with a stored passphrase.
    """

    mock_config = mock.mock_open(read_data='KEY_PASSPHRASE1=Hell0')
    with mock.patch('builtins.open' if six.PY3 else '__builtin__.open', mock_config):
        monkeypatch.setattr(networkdeprecations.os, 'listdir', _listdir_keys)
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
        networkdeprecations.process()
        assert reporting.create_report.called


def test_ifcfg_dynamic_wep(monkeypatch):
    """
    Report if there's a dynamic WEP sysconfig.
    """

    DYNAMIC_WEP_SYSCONFIG = textwrap.dedent("""
        ESSID=dynwep1
        MODE=Managed
        KEY_MGMT=IEEE8021X  # Dynamic WEP!
        TYPE=Wireless
        NAME=dynwep1
    """)

    mock_config = mock.mock_open(read_data=DYNAMIC_WEP_SYSCONFIG)
    with mock.patch('builtins.open' if six.PY3 else '__builtin__.open', mock_config):
        monkeypatch.setattr(networkdeprecations.os, 'listdir', _listdir_ifcfg)
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
        networkdeprecations.process()
        assert reporting.create_report.called
