import errno
from functools import partial

import mock
import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import restrictedpcisscanner
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
        "mcs_socket",
        "mcs_available",
        "global_files_exists",
        "bad_data",
        "json_returns_first",
        "json_returns_second",
    ),
    [
        # Should use global files
        (
            "not existing host of the mcs",
            False,
            True,
            False,
            unsupported_driver_names_example,
            unsupported_pci_ids_example,
        ),
        # Should use global files (because it is preferred)
        (
            "existing host",
            True,
            True,
            False,
            unsupported_driver_names_example,
            unsupported_pci_ids_example,
        ),
        # Should use mcs (calls are mocked)
        (
            "existing host",
            True,
            False,
            False,
            unsupported_driver_names_example,
            unsupported_pci_ids_example,
        ),
        # Should raise StopActorExecutionError
        (
            "not existing host",
            False,
            False,
            True,
            unsupported_driver_names_example,
            unsupported_pci_ids_example,
        ),
        # Should use global files, which has bad data. Should raise StopActorExecutionError
        (
            "not existing host of the mcs",
            False,
            True,
            True,
            some_very_bad_data,
            some_very_bad_data,
        ),
        # Should use global files, which has bad data. Should raise StopActorExecutionError
        (
            "not existing host of the mcs",
            False,
            True,
            True,
            some_bad_data,
            some_bad_data,
        ),
        # Should use mcs, which has bad data. Should raise StopActorExecutionError
        (
            "existing host",
            True,
            False,
            True,
            some_very_bad_data,
            some_very_bad_data,
        ),
        # Should use mcs, which has bad data. Should raise StopActorExecutionError
        (
            "existing host",
            True,
            False,
            True,
            some_bad_data,
            some_bad_data,
        ),
    ],
)
def test_basic_restricted_pci_scanner(
    monkeypatch,
    mcs_socket,
    mcs_available,
    global_files_exists,
    bad_data,
    json_returns_first,
    json_returns_second,
):
    """Test main actor function."""
    monkeypatch.setattr(
        api,
        "current_actor",
        CurrentActorMocked(
            envars={
                "LEAPP_DEVEL_PCIS_HOST": mcs_socket,
            }
        ),
    )
    monkeypatch.setattr(api, "produce", produce_mocked())
    if global_files_exists:
        json_loads_mock = json_loads_mock_gen(
            json_returns_first, json_returns_second
        )
        monkeypatch.setattr(
            restrictedpcisscanner.json,
            "load",
            value=next(json_loads_mock),
        )
        monkeypatch.setattr(
            restrictedpcisscanner,
            "get_restricted_pcis_offline",
            value=partial(
                restrictedpcisscanner.get_restricted_pcis_offline,
                # no need to provide any data, because we mocked the
                #   json.loads
                _open=mock_open(read_data=""),
            ),
        )
        if bad_data:
            with pytest.raises(StopActorExecutionError):
                restrictedpcisscanner.produce_restricted_pcis()
            return
        restrictedpcisscanner.produce_restricted_pcis()

    if not global_files_exists and mcs_available:
        pool_manager_mock = mock.Mock()
        get_restricted_pcis_offline = mock.Mock(
            side_effect=FileNotFoundError()
        )
        json_loads_mock = json_loads_mock_gen(
            json_returns_first, json_returns_second
        )
        # even though FileNotFoundError raised as side effect, the error
        # number is None (should be 2), so we have to mock the ENOENT
        monkeypatch.setattr(errno, "ENOENT", value=None)

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

        if bad_data:
            with pytest.raises(StopActorExecutionError):
                restrictedpcisscanner.produce_restricted_pcis()
            return
        restrictedpcisscanner.produce_restricted_pcis()

        pool_manager_mock.assert_called_once()
    if not global_files_exists and not mcs_available:
        with pytest.raises(StopActorExecutionError):
            restrictedpcisscanner.produce_restricted_pcis()
        return
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
