import pytest
import pyudev
import six
from mock import mock_open, patch

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import biosdevname
from leapp.libraries.stdlib import api
from leapp.models import Interface, PCIAddress


class LoggerMocked(object):
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


class pyudev_enum_mock(object):
    def __init__(self, vendor):
        self.vendor = vendor

    def match_sys_name(self, _):
        class dev(object):
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


def test_all_interfaces_biosdevname(monkeypatch):
    pci_info = PCIAddress(domain="domain", function="function", bus="bus", device="device")

    interfaces = [
        Interface(
            name="eth0", mac="mac", vendor="dell", pci_info=pci_info, devpath="path", driver="drv"
        )
    ]
    assert not biosdevname.all_interfaces_biosdevname(interfaces)
    interfaces = [
        Interface(
            name="em0", mac="mac", vendor="dell", pci_info=pci_info, devpath="path", driver="drv"
        )
    ]
    assert biosdevname.all_interfaces_biosdevname(interfaces)
    interfaces = [
        Interface(
            name="p0p22", mac="mac", vendor="dell", pci_info=pci_info, devpath="path", driver="drv"
        )
    ]
    assert biosdevname.all_interfaces_biosdevname(interfaces)

    interfaces = [
        Interface(
            name="p1p2", mac="mac", vendor="dell", pci_info=pci_info, devpath="path", driver="drv"
        ),
        Interface(
            name="em2", mac="mac", vendor="dell", pci_info=pci_info, devpath="path", driver="drv"
        ),
    ]
    assert biosdevname.all_interfaces_biosdevname(interfaces)

    interfaces = [
        Interface(
            name="p1p2", mac="mac", vendor="dell", pci_info=pci_info, devpath="path", driver="drv"
        ),
        Interface(
            name="em2", mac="mac", vendor="dell", pci_info=pci_info, devpath="path", driver="drv"
        ),
        Interface(
            name="eth0", mac="mac", vendor="dell", pci_info=pci_info, devpath="path", driver="drv"
        ),
    ]
    assert not biosdevname.all_interfaces_biosdevname(interfaces)


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
