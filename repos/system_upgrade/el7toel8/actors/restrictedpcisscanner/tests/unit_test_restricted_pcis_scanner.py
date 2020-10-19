import mock
import pytest

from leapp.libraries.actor import restrictedpcisscanner
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import RestrictedPCIDevice, RestrictedPCIDevices

unsupported_driver_names_example = {
    "devices": {
        "3w-9xxx": {
            "pci_id": "nan",
            "driver_name": "3w-9xxx",
            "device_name": "3w-9xxx",
            "available_rhel7": 1,
            "supported_rhel7": 0,
            "available_rhel8": 0,
            "supported_rhel8": 0,
            "available_rhel9": 0,
            "supported_rhel9": 0,
            "comment": "nan",
        },
        "3w-sas": {
            "pci_id": "nan",
            "driver_name": "3w-sas",
            "device_name": "3w-sas",
            "available_rhel7": 1,
            "supported_rhel7": 0,
            "available_rhel8": 0,
            "supported_rhel8": 0,
            "available_rhel9": 0,
            "supported_rhel9": 0,
            "comment": "nan",
        },
    }
}


unsupported_pci_ids_example = {
    "devices": {
        "0x1000:0x0060": {
            "pci_id": "0x1000:0x0060",
            "driver_name": "megaraid_sas",
            "device_name": "SAS1078R",
            "available_rhel7": 1,
            "supported_rhel7": 1,
            "available_rhel8": 0,
            "supported_rhel8": 0,
            "available_rhel9": 0,
            "supported_rhel9": 0,
            "comment": "nan",
        },
        "0x1000:0x0064": {
            "pci_id": "0x1000:0x0064",
            "driver_name": "mpt2sas",
            "device_name": "SAS2116_1",
            "available_rhel7": 1,
            "supported_rhel7": 1,
            "available_rhel8": 0,
            "supported_rhel8": 0,
            "available_rhel9": 0,
            "supported_rhel9": 0,
            "comment": "nan",
        },
    }
}


def json_loads_mock_gen():
    """
    Generator used for mocking the json.loads call.

    It is needed to make it possible returning two different values when
    called json.loads first a nd second time.
    """
    yield lambda _: unsupported_driver_names_example
    yield lambda _: unsupported_pci_ids_example


@pytest.mark.parametrize(
    ("host", "mock_api_call"),
    [
        ("not existing host", False),
        ("10.0.79.153:8000", True),
    ],
)
def test_basic_restricted_pci_scanner(monkeypatch, host, mock_api_call):
    monkeypatch.setattr(
        api,
        "current_actor",
        CurrentActorMocked(
            envars={
                "LEAPP_DEVEL_UNSUPPORTED_PCIS_HOST": host,
            }
        ),
    )
    monkeypatch.setattr(api, "produce", produce_mocked())
    if mock_api_call:
        pool_manager_mock = mock.Mock()
        get_restricted_pcis_offline = mock.Mock()
        json_loads_mock = json_loads_mock_gen()

        monkeypatch.setattr(
            restrictedpcisscanner.urllib3,
            "PoolManager",
            value=pool_manager_mock,
        )
        monkeypatch.setattr(
            restrictedpcisscanner.json,
            "loads",
            value=next(json_loads_mock),
        )
        monkeypatch.setattr(
            restrictedpcisscanner,
            "get_restricted_pcis_offline",
            value=get_restricted_pcis_offline,
        )

        restrictedpcisscanner.produce_restricted_pcis()

        pool_manager_mock.assert_called_once()
        get_restricted_pcis_offline.assert_not_called()
    else:
        restrictedpcisscanner.produce_restricted_pcis()
    assert len(api.produce.model_instances) == 1
    assert isinstance(api.produce.model_instances[0], RestrictedPCIDevices)
    assert isinstance(
        tuple(api.produce.model_instances[0].driver_names.values())[0],
        RestrictedPCIDevice,
    )
    assert isinstance(
        tuple(api.produce.model_instances[0].pci_ids.values())[0],
        RestrictedPCIDevice,
    )


@pytest.mark.skip(reason="Use only for updating the local data")
def test_update_local_data(monkeypatch):
    """
    Update the locally stored data about restricted pci devices.

    It makes a call to the real microservice with the data and stores it as
    json.
    """
    import urllib3  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(
        api,
        "current_actor",
        CurrentActorMocked(),
    )
    http = urllib3.PoolManager()
    restrictedpcisscanner.get_restricted_pcis(http, update_local_data=True)
