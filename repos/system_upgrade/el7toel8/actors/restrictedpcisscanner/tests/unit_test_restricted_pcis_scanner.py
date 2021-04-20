import errno
from functools import partial

import mock
import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import restrictedpcisscanner
from leapp.libraries.common import fetch
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import RestrictedPCIDevice, RestrictedPCIDevices


try:
    # python3
    from unittest.mock import mock_open
except ImportError:
    # python2
    from mock import mock_open  # pylint: disable=ungrouped-imports

    FileNotFoundError = IOError  # pylint: disable=redefined-builtin

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

some_very_bad_data = {"bad": "data"}
some_bad_data = {"devices": "not here"}


def blank_fn(should_return, *args, **kwargs):
    """
    Just a blank fn which accepts anything and returns what should_return.
    """
    return should_return


def json_loads_mock_gen(returns_first, returns_second):
    """
    Generator used for mocking the json.loads call.

    :param returns_first: defines which data will be returned by the json.loads when called first time
    :param returns_second: defines which data will be returned by the json.loads when called the second time

    It is needed to make it possible returning two different values when
    called json.loads first and the second time.
    """
    yield partial(blank_fn, returns_first)
    yield partial(blank_fn, returns_second)


@pytest.mark.parametrize(
    (
        "bad_data",
        "json_returns_first",
        "json_returns_second",
    ),
    [
        # Correct data
        (
            False,
            unsupported_driver_names_example,
            unsupported_pci_ids_example,
        ),
        # Bad data. Should raise StopActorExecutionError
        (
            True,
            some_very_bad_data,
            some_very_bad_data,
        ),
        # Bad data. Should raise StopActorExecutionError
        (
            True,
            some_bad_data,
            some_bad_data,
        ),
    ],
)
def test_basic_restricted_pci_scanner(
    monkeypatch,
    bad_data,
    json_returns_first,
    json_returns_second,
):
    monkeypatch.setattr(api, "produce", produce_mocked())
    json_loads_mock = json_loads_mock_gen(
        json_returns_first, json_returns_second
    )
    monkeypatch.setattr(
        fetch,
        "read_or_fetch",
        blank_fn,
    )
    monkeypatch.setattr(
        restrictedpcisscanner.json,
        "loads",
        value=next(json_loads_mock),
    )

    if bad_data:
        with pytest.raises(StopActorExecutionError):
            restrictedpcisscanner.produce_restricted_pcis()
        return

    restrictedpcisscanner.produce_restricted_pcis()
    assert len(api.produce.model_instances) == 1
    assert isinstance(api.produce.model_instances[0], RestrictedPCIDevices)
    assert isinstance(
        api.produce.model_instances[0].driver_names[0],
        RestrictedPCIDevice,
    )
    assert isinstance(
        api.produce.model_instances[0].pci_ids[0],
        RestrictedPCIDevice,
    )
