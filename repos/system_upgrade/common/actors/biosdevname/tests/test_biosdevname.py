import pytest
import pyudev
import six
from mock import mock_open, patch

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import biosdevname
from leapp.libraries.stdlib import api
from leapp.models import Interface, PCIAddress


class LoggerMocked:
    def __init__(self):
        self.infomsg = None

    def info(self, *args):
        self.infomsg = args

    def __call__(self):
        return self


def test_biosdevname_disabled(monkeypatch):
    mock_config = mock_open(read_data="biosdevname=0")
    with patch("builtins.open" if six.PY3 else "__builtin__.open", mock_config):
        assert biosdevname.is_biosdevname_disabled()


def test_biosdevname_enabled(monkeypatch):
    mock_config = mock_open(read_data="biosdevname=1")
    with patch("builtins.open" if six.PY3 else "__builtin__.open", mock_config):
        assert not biosdevname.is_biosdevname_disabled()


class pyudev_enum_mock:
    def __init__(self, vendor):
        self.vendor = vendor

    def match_sys_name(self, _):
        class dev:
            attributes = {'sys_vendor': self.vendor}

        return [dev()]

    def match_subsystem(self, _):
        return self

    def __call__(self, _):
        return self


def test_is_vendor_is_dell(monkeypatch):
    monkeypatch.setattr(pyudev, "Enumerator", pyudev_enum_mock("Dell"))
    assert biosdevname.is_vendor_dell()


def test_is_vendor_is_not_dell(monkeypatch):
    monkeypatch.setattr(pyudev, "Enumerator", pyudev_enum_mock("HP"))
    assert not biosdevname.is_vendor_dell()


def _gen_ifaces_by_names(names):
    pci = PCIAddress(domain="0000", bus="3e", function="00", device="PCI bridge")
    interfaces = []
    for nic_name in names:
        interfaces.append(Interface(
            name=nic_name,
            devpath="path",
            driver="drv",
            mac="52:54:00:0b:4a:6d",
            pci_info=pci,
            vendor="dell",
        ))
    return interfaces


@pytest.mark.parametrize(("interface_names", "expected_result"), (
    (["eth0"], False),
    (["preem0"], False),
    (["em0post"], False),
    (["prep0p22"], False),
    (["p0p22post"], False),
    (["em0"], True),
    (["p0p22"], True),
    (["em2", "p1p22"], True),
    (["p1p2", "em2", "eth0"], False)
))
def test_all_interfaces_biosdevname(interface_names, expected_result):
    interfaces = _gen_ifaces_by_names(interface_names)
    assert biosdevname.all_interfaces_biosdevname(interfaces) == expected_result


def test_enable_biosdevname(monkeypatch):
    result = []
    monkeypatch.setattr(api, 'current_logger', LoggerMocked())
    monkeypatch.setattr(api, 'produce', result.append)

    biosdevname.enable_biosdevname()
    assert (
        "Biosdevname naming scheme in use, explicitly enabling biosdevname on the target RHEL system"
        in api.current_logger.infomsg
    )
    assert result[0].key == "biosdevname"
    assert result[0].value == "1"


def test_check_biosdevname(monkeypatch):
    def persistent_net_names_mocked(*models):
        yield None

    monkeypatch.setattr(api, "consume", persistent_net_names_mocked)
    monkeypatch.setattr(biosdevname, "is_biosdevname_disabled", lambda: False)
    with pytest.raises(StopActorExecutionError):
        biosdevname.check_biosdevname()
