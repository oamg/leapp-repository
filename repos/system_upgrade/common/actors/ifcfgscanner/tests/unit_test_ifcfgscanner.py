import errno
import textwrap
from os.path import basename

import mock
import six

from leapp.libraries.actor import ifcfgscanner
from leapp.libraries.common.testutils import make_OSError, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import IfCfg

_builtins_open = "builtins.open" if six.PY3 else "__builtin__.open"


def _listdir_ifcfg(path):
    if path == ifcfgscanner.SYSCONFIG_DIR:
        return ["ifcfg-net0"]
    raise make_OSError(errno.ENOENT)


def _listdir_ifcfg2(path):
    if path == ifcfgscanner.SYSCONFIG_DIR:
        return ["ifcfg-net0", "ifcfg-net1"]
    raise make_OSError(errno.ENOENT)


def _exists_ifcfg(filename):
    return basename(filename).startswith("ifcfg-")


def _exists_keys(filename):
    if _exists_ifcfg(filename):
        return True
    return basename(filename).startswith("keys-")


def test_no_conf(monkeypatch):
    """
    No report if there are no ifcfg files.
    """

    monkeypatch.setattr(ifcfgscanner, "listdir", lambda _: ())
    monkeypatch.setattr(api, "produce", produce_mocked())
    ifcfgscanner.process()
    assert not api.produce.called


def test_ifcfg1(monkeypatch):
    """
    Parse a single ifcfg file.
    """

    ifcfg_file = textwrap.dedent("""
        TYPE=Wireless  # Some comment
        # Another comment
        ESSID=wep1
        NAME="wep1"
        MODE='Managed'   # comment
        WEP_KEY_FLAGS=ask
        SECURITYMODE=open
        DEFAULTKEY=1
        KEY_TYPE=key
    """)

    mock_config = mock.mock_open(read_data=ifcfg_file)
    with mock.patch(_builtins_open, mock_config):
        monkeypatch.setattr(ifcfgscanner, "listdir", _listdir_ifcfg)
        monkeypatch.setattr(ifcfgscanner.path, "exists", _exists_ifcfg)
        monkeypatch.setattr(api, "produce", produce_mocked())
        ifcfgscanner.process()

        assert api.produce.called == 1
        assert len(api.produce.model_instances) == 1
        ifcfg = api.produce.model_instances[0]
        assert isinstance(ifcfg, IfCfg)
        assert ifcfg.filename == "/etc/sysconfig/network-scripts/ifcfg-net0"
        assert ifcfg.secrets is None
        assert len(ifcfg.properties) == 8
        assert ifcfg.properties[0].name == "TYPE"
        assert ifcfg.properties[0].value == "Wireless"
        assert ifcfg.properties[1].name == "ESSID"
        assert ifcfg.properties[1].value == "wep1"
        assert ifcfg.properties[2].name == "NAME"
        assert ifcfg.properties[2].value == "wep1"
        assert ifcfg.properties[3].name == "MODE"
        assert ifcfg.properties[3].value == "Managed"


def test_ifcfg2(monkeypatch):
    """
    Parse two ifcfg files.
    """

    mock_config = mock.mock_open(read_data="TYPE=Ethernet")
    with mock.patch(_builtins_open, mock_config):
        monkeypatch.setattr(ifcfgscanner, "listdir", _listdir_ifcfg2)
        monkeypatch.setattr(ifcfgscanner.path, "exists", _exists_ifcfg)
        monkeypatch.setattr(api, "produce", produce_mocked())
        ifcfgscanner.process()

        assert api.produce.called == 2
        assert len(api.produce.model_instances) == 2
        ifcfg = api.produce.model_instances[0]
        assert isinstance(ifcfg, IfCfg)


def test_ifcfg_key(monkeypatch):
    """
    Report ifcfg secrets from keys- file.
    """

    mock_config = mock.mock_open(read_data="KEY_PASSPHRASE1=Hell0")
    with mock.patch(_builtins_open, mock_config):
        monkeypatch.setattr(ifcfgscanner, "listdir", _listdir_ifcfg)
        monkeypatch.setattr(ifcfgscanner.path, "exists", _exists_keys)
        monkeypatch.setattr(api, "produce", produce_mocked())
        ifcfgscanner.process()

        assert api.produce.called == 1
        assert len(api.produce.model_instances) == 1
        ifcfg = api.produce.model_instances[0]
        assert isinstance(ifcfg, IfCfg)
        assert ifcfg.filename == "/etc/sysconfig/network-scripts/ifcfg-net0"
        assert len(ifcfg.secrets) == 1
        assert ifcfg.secrets[0].name == "KEY_PASSPHRASE1"
        assert ifcfg.secrets[0].value is None
