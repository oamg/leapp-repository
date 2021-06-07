from leapp.libraries.common import persistentnetnames
from leapp.libraries.common.testutils import produce_mocked
from leapp.libraries.stdlib import api


class AttributesTest(object):
    def __init__(self):
        self.attributes = {
            'address': b'fa:16:3e:cd:26:5a'
        }

    def get(self, attribute):
        if attribute in self.attributes:
            return self.attributes[attribute]
        raise KeyError


class DeviceTest(object):
    def __init__(self):
        self.dict_data = {
             'ID_NET_DRIVER': 'virtio_net',
             'ID_VENDOR_ID': '0x1af4',
             'ID_PATH': 'pci-0000:00:03.0',
        }

    def __getitem__(self, key):
        if key in self.dict_data:
            return self.dict_data[key]
        raise KeyError

    @property
    def sys_name(self):
        return 'eth'

    @property
    def device_path(self):
        return '/devices/pci0000:00/0000:00:03.0/virtio0/net/eth0'

    @property
    def attributes(self):
        return AttributesTest()


def provide_test_interfaces():
    return [DeviceTest()]


def test_getting_interfaces(monkeypatch):
    monkeypatch.setattr(persistentnetnames, 'physical_interfaces', provide_test_interfaces)
    monkeypatch.setattr(api, 'produce', produce_mocked())
    interface = next(persistentnetnames.interfaces())
    assert interface.name
    assert interface.devpath
    assert interface.driver
    assert interface.vendor
    assert interface.pci_info
    assert interface.mac
