import errno
import json

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import restrictedpcisscanner
from leapp.libraries.common import fetch
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import RestrictedPCIDevice, RestrictedPCIDevices


unsupported_driver_names_example = {
    'devices': {
        '3w-9xxx': {
            'pci_id': 'nan',
            'driver_name': '3w-9xxx',
            'device_name': '3w-9xxx',
            'available_rhel7': 1,
            'supported_rhel7': 0,
            'available_rhel8': 0,
            'supported_rhel8': 0,
            'available_rhel9': 0,
            'supported_rhel9': 0,
            'comment': 'nan',
        },
        '3w-sas': {
            'pci_id': 'nan',
            'driver_name': '3w-sas',
            'device_name': '3w-sas',
            'available_rhel7': 1,
            'supported_rhel7': 1,
            'available_rhel8': 1,
            'supported_rhel8': 1,
            'available_rhel9': 0,
            'supported_rhel9': 0,
            'comment': 'nan',
        },
    }
}

expected_driver_names_devices = {
    '3w-9xxx': RestrictedPCIDevice(
            pci_id='nan',
            driver_name='3w-9xxx',
            device_name='3w-9xxx',
            available_rhel7=1,
            supported_rhel7=0,
            available_rhel8=0,
            supported_rhel8=0,
            available_rhel9=0,
            supported_rhel9=0,
            comment='nan',
            available=[7],
            supported=[],
    ),
    '3w-sas': RestrictedPCIDevice(
            pci_id='nan',
            driver_name='3w-sas',
            device_name='3w-sas',
            available_rhel7=1,
            supported_rhel7=1,
            available_rhel8=1,
            supported_rhel8=1,
            available_rhel9=0,
            supported_rhel9=0,
            comment='nan',
            available=[7, 8],
            supported=[7, 8],
    ),
}


unsupported_pci_ids_example = {
    'devices': {
        '0x1000:0x0060': {
            'pci_id': '0x1000:0x0060',
            'driver_name': 'megaraid_sas',
            'device_name': 'SAS1078R',
            'available_rhel7': 1,
            'supported_rhel7': 1,
            'available_rhel8': 0,
            'supported_rhel8': 0,
            'available_rhel9': 0,
            'supported_rhel9': 0,
            'comment': 'nan',
        },
        '0x1000:0x0064': {
            'pci_id': '0x1000:0x0064',
            'driver_name': 'mpt2sas',
            'device_name': 'SAS2116_1',
            'available_rhel7': 1,
            'supported_rhel7': 1,
            'available_rhel8': 1,
            'supported_rhel8': 0,
            'available_rhel9': 0,
            'supported_rhel9': 0,
            'comment': 'nan',
        },
    }
}

expected_driver_names_devices = {
    '0x1000:0x0064': RestrictedPCIDevice(
            pci_id='0x1000:0x0060',
            driver_name='megaraid_sas',
            device_name='SAS1078R',
            available_rhel7=1,
            supported_rhel7=1,
            available_rhel8=0,
            supported_rhel8=0,
            available_rhel9=0,
            supported_rhel9=0,
            comment='nan',
            available=[7],
            supported=[],
    ),
    '0x1000:0x0064': RestrictedPCIDevice(
            pci_id='0x1000:0x0064',
            driver_name='mpt2sas',
            device_name='SAS2116_1',
            available_rhel7=1,
            supported_rhel7=1,
            available_rhel8=0,
            supported_rhel8=0,
            available_rhel9=0,
            supported_rhel9=0,
            comment='nan',
            available=[7, 8],
            supported=[7],
    ),
}

some_very_bad_data = {'bad': 'data'}
some_bad_data = {'devices': 'not here'}


class Mocked_fetch():

    def __init__(self, pci_ids_data, driver_names_data):
        self.pci_ids_data = pci_ids_data
        self.driver_names_data = driver_names_data
        self.called = 0
        self.filenames = []

    def __call__(self, filename):
        if filename == restrictedpcisscanner.UNSUPPORTED_PCI_IDS_FILE:
            return self.pci_ids_data
        if filename == restrictedpcisscanner.UNSUPPORTED_DRIVER_NAMES_FILE:
            return self.driver_names_data
        raise ValueError("Trying to fetch unexpected file: {} (maybe unit test needs update?)".format(filename))


@pytest.mark.parametrize(("bad_data", "pci_ids_data", "driver_names_data"), (
    (False, unsupported_pci_ids_example, unsupported_driver_names_example),  # OK
    (True, some_very_bad_data, some_very_bad_data),  # KO
    (True, some_bad_data, some_bad_data),  # KO
))
def test_basic_restricted_pci_scanner(monkeypatch, bad_data, pci_ids_data, driver_names_data):
    monkeypatch.setattr(api, "produce", produce_mocked())
    monkeypatch.setattr(fetch, "read_or_fetch", mocked_fetch(pci_ids_data, driver_names_data))

    if bad_data:
        with pytest.raises(StopActorExecutionError):
            restrictedpcisscanner.produce_restricted_pcis()
        return

    restrictedpcisscanner.produce_restricted_pcis()
    assert len(api.produce.model_instances) == 1
    assert isinstance(api.produce.model_instances[0], RestrictedPCIDevices)
    for dname in api.produce.model_instances[0].driver_names:
        assert dname == expected_driver_names_devices[dname.driver_name]
    for dname in api.produce.model_instances[0].pci_ids:
        assert dname == expected_driver_names_devices[dname.device_name]
