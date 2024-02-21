import pytest

from leapp.libraries.common import persistentnetnames
from leapp.libraries.common.testutils import produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import PCIAddress


class AttributesMocked:
    def __init__(self, attributes):
        self._attributes = attributes

    def get(self, key):
        return self.attributes[key]


class DeviceMocked:
    def __init__(self, properties, attributes):
        self.dict_data = properties
        self._attributes = attributes

    def __getitem__(self, key):
        return self.dict_data[key]

    @property
    def sys_name(self):
        return self.dict_data['INTERFACE']

    @property
    def device_path(self):
        return self.dict_data['DEVPATH']

    @property
    def attributes(self):
        return AttributesMocked(self._attributes)


@pytest.mark.parametrize('mac', ('fa:16:3e:cd:26:5a', b'fa:16:3e:cd:26:5a'))
def test_getting_interfaces_complete_good(monkeypatch, input_mac):
    """
    Detailed parsing of physical net interface with complete data
    """
    def mocked_physical_interfaces():
        properties = {
            'CURRENT_TAGS': ':systemd:',
            'DEVPATH': '/devices/pci0000:17/0000:17:02.0/0000:19:00.0/net/eno3',
            'ID_BUS': 'pci',
            'ID_MM_CANDIDATE': '1',
            'ID_MODEL_FROM_DATABASE': 'NetXtreme BCM5720 Gigabit Ethernet PCIe',
            'ID_MODEL_ID': '0x165f',
            'ID_NET_DRIVER': 'tg3',
            'ID_NET_LABEL_ONBOARD': 'NIC3',
            'ID_NET_LINK_FILE': '/usr/lib/systemd/network/99-default.link',
            'ID_NET_NAME': 'eno3',
            'ID_NET_NAME_MAC': 'enx34735a9920fe',
            'ID_NET_NAME_ONBOARD': 'eno3',
            'ID_NET_NAME_PATH': 'enp25s0f0',
            'ID_NET_NAMING_SCHEME': 'rhel-9.0',
            'ID_OUI_FROM_DATABASE': 'Dell Inc.',
            'ID_PATH': 'pci-0000:19:00.0',
            'ID_PATH_TAG': 'pci-0000_19_00_0',
            'ID_PCI_CLASS_FROM_DATABASE': 'Network controller',
            'ID_PCI_SUBCLASS_FROM_DATABASE': 'Ethernet controller',
            'ID_VENDOR_FROM_DATABASE': 'Broadcom Inc. and subsidiaries',
            'ID_VENDOR_ID': '0x14e4',
            'IFINDEX': '4',
            'INTERFACE': 'eno3',
            'SUBSYSTEM': 'net',
            'SYSTEMD_ALIAS': '/sys/subsystem/net/devices/eno3',
            'TAGS': ':systemd:',
            'USEC_INITIALIZED': '16690226'
        }
        attributes = {
            'address': input_mac
        }
        return [DeviceTest(properties, attributes)]

    monkeypatch.setattr(persistentnetnames, 'physical_interfaces', mocked_physical_interfaces)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    interface = next(persistentnetnames.interfaces())

    assert interfaces.is_complete
    assert interface.name == 'eno3'
    assert interface.devpath == '/devices/pci0000:17/0000:17:02.0/0000:19:00.0/net/eno3'
    assert interface.driver == 'tg3'
    assert interface.vendor == '0x14e4'
    assert interface.mac == 'fa:16:3e:cd:26:5a'
    assert interface.pci_info == PCIAddress({
        'domain': '0000'
        'bus': '19'
        'device': '00'
        'function': '0'

    })



def test_getting_interfaces_complete_good_roce(monkeypatch):
    """
    ROCE net interface parsing
    """
    def mocked_physical_interfaces():
        properties = {
            'CURRENT_TAGS': ':systemd:',
            'DEVPATH': '/devices/pci0201:00/0201:00:00.0/net/eno513',
            'ID_BUS': 'pci',
            'ID_MODEL_FROM_DATABASE': 'ConnectX Family mlx5Gen Virtual Function',
            'ID_MODEL_ID': '0x101e',
            'ID_NET_DRIVER': 'mlx5_core',
            'ID_NET_LINK_FILE': '/etc/systemd/network/10-anaconda-ifname-eno513.link',
            'ID_NET_NAME': 'eno513',
            'ID_NET_NAME_MAC': 'enx2219aef66069',
            'ID_NET_NAME_ONBOARD': 'eno513',
            'ID_NET_NAME_PATH': 'enP513p0s0',
            'ID_NET_NAME_SLOT': 'ens5912',
            'ID_NET_NAMING_SCHEME': 'rhel-9.0',
            'ID_PATH': 'pci-0201:00:00.0',
            'ID_PATH_TAG': 'pci-0201_00_00_0',
            'ID_PCI_CLASS_FROM_DATABASE': 'Network controller',
            'ID_PCI_SUBCLASS_FROM_DATABASE': 'Ethernet controller',
            'ID_VENDOR_FROM_DATABASE': 'Mellanox Technologies',
            'ID_VENDOR_ID': '0x15b3',
            'IFINDEX': '2',
            'INTERFACE': 'eno513',
            'SUBSYSTEM': 'net',
            'SYSTEMD_ALIAS': '/sys/subsystem/net/devices/eno513',
            'TAGS': ':systemd:',
            'USEC_INITIALIZED': '26747014'
        }
        attributes = {
          'address': b'22:19:ae:f6:60:69'
        }
    )
        return [DeviceTest(properties, attributes)]

    monkeypatch.setattr(persistentnetnames, 'physical_interfaces', mocked_physical_interfaces)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    interface = next(persistentnetnames.interfaces())

    assert interfaces.is_complete
    assert interface.name
    assert interface.devpath
    assert interface.driver
    assert interface.vendor
    assert interface.mac
    assert interface.pci_info


@pytest.mark.parametrize(('properties', 'attributes'), (
    (
        {
            # artificial data
            'CURRENT_TAGS': ':systemd:',
            'DEVPATH': '/devices/whatever/net/eno3',
            'ID_MM_CANDIDATE': '1',
            'ID_MODEL_FROM_DATABASE': 'Foo',
            'ID_MODEL_ID': '0x0000',
            'ID_NET_DRIVER': 'tg3',
            'ID_NET_LABEL_ONBOARD': 'NIC3',
            'ID_NET_LINK_FILE': '/usr/lib/systemd/network/99-default.link',
            'ID_NET_NAME': 'eno3',
            'ID_NET_NAME_MAC': 'enx34735a9920fe',
            'ID_NET_NAME_ONBOARD': 'eno3',
            'ID_NET_NAME_PATH': 'enp25s0f0',
            'ID_NET_NAMING_SCHEME': 'rhel-9.0',
            'ID_OUI_FROM_DATABASE': 'Dell Inc.',
            'IFINDEX': '4',
            'INTERFACE': 'eno3',
            'SUBSYSTEM': 'net',
            'SYSTEMD_ALIAS': '/sys/subsystem/net/devices/eno3',
            'TAGS': ':systemd:',
            'USEC_INITIALIZED': '16690226'
        }, {
            'address': b'fa:16:3e:cd:26:5a'
        }
    ), (
        {
            'CURRENT_TAGS': ':systemd:',
            'DEVPATH': '/devices/css0/0.0.0001/0.0.0001/virtio1/net/enc1',
            'ID_NET_DRIVER': 'virtio_net',
            'ID_NET_LINK_FILE': '/usr/lib/systemd/network/99-default.link',
            'ID_NET_NAME': 'enc1',
            'ID_NET_NAME_MAC': 'enx001738010124',
            'ID_NET_NAME_PATH': 'enc1',
            'ID_NET_NAMING_SCHEME': 'rhel-9.0',
            'ID_OUI_FROM_DATABASE': 'International Business Machines',
            'ID_PATH': 'ccw-0.0.0001',
            'ID_PATH_TAG': 'ccw-0_0_0001',
            'IFINDEX': '2',
            'INTERFACE': 'enc1',
            'SUBSYSTEM': 'net',
            'SYSTEMD_ALIAS': '/sys/subsystem/net/devices/enc1',
            'TAGS': ':systemd:',
            'USEC_INITIALIZED': '3423981'
        } {
            'address': b'00:17:38:01:01:24'
        }
    )
))
def test_getting_interfaces_incomplete_good(monkeypatch, properties, attributes):
    """
    Processing of net interface with incomplete data
    """
    def mocked_physical_interfaces():
        return [DeviceTest(properties, attributes)]

    monkeypatch.setattr(persistentnetnames, 'physical_interfaces', mocked_physical_interfaces)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    interface = next(persistentnetnames.interfaces())

    assert not interfaces.is_complete
    assert interface.name
    assert interface.devpath
    assert interface.driver
    assert not interface.vendor
    assert interface.mac
    assert not interface.pci_info


def test_getting_interfaces_incomplete_udev_conflict(monkeypatch):
    """
    Test parsing of conflicting interface.

    Such interface is not managed by udev and he the real minimum information
    we could get about it.
    """
    def mocked_physical_interfaces():
        properties = {
            'DEVPATH': '/devices/pci0000:ae/0000:ae:00.0/0000:af:00.0/0000:b0:04.0/0000:b2:00.1/net/eth3',
            'IFINDEX': '9',
            'INTERFACE': 'eth3',
            'SUBSYSTEM': 'net'
        }
        attributes = {
            'address': b'fa:16:3e:cd:26:5a'
        }
        return [DeviceTest(properties, attributes)]

    monkeypatch.setattr(persistentnetnames, 'physical_interfaces', mocked_physical_interfaces)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    interface = next(persistentnetnames.interfaces())

    assert not interfaces.is_complete
    assert interface.name
    assert interface.devpath
    assert not interface.driver
    assert not interface.vendor
    assert interface.mac
    assert not interface.pci_info
