from leapp.libraries.actor import deviceanddriverdeprecationdataload as ddddload
from leapp.libraries.common import fetch

TEST_DATA = {
    'data': [
        {
            'available_in_rhel': [8, 9],
            'deprecation_announced': '',
            'device_id': 'unsupported:id',
            'device_name': 'Unsupported device type',
            'device_type': 'unsupported',
            'driver_name': '',
            'maintained_in_rhel': [],
        },
        {
            'available_in_rhel': [8, 9],
            'deprecation_announced': '',
            'device_id': 'x86_64:amd:25:1',
            'device_name': 'Supported Family 19h',
            'device_type': 'cpu',
            'driver_name': '',
            'maintained_in_rhel': [],
        },
        {
            'available_in_rhel': [],
            'deprecation_announced': '',
            'device_id': 'x86_64:amd:25:[2-255]',
            'device_name': 'Unsupported Family 19h',
            'device_type': 'cpu',
            'driver_name': '',
            'maintained_in_rhel': [],
        },
        {
            'available_in_rhel': [7],
            'deprecation_announced': '',
            'device_id': '0x10df:0xf180',
            'device_name': 'Emulex Corporation: LPSe12002 EmulexSecure Fibre Channel Adapter',
            'device_type': 'pci',
            'driver_name': 'lpfc',
            'maintained_in_rhel': [7],
        },
    ]
}


def test_filtered_load(monkeypatch):
    produced = []

    def load_data_asset_mock(*args, **kwargs):
        return TEST_DATA

    monkeypatch.setattr(fetch, 'load_data_asset', load_data_asset_mock)
    monkeypatch.setattr(ddddload.api, 'produce', lambda *v: produced.extend(v))

    ddddload.process()

    assert produced
    assert len(produced[0].entries) == 3
    assert not any([e.device_type == 'unsupported' for e in produced[0].entries])
