import mock
import pytest

from leapp.libraries.actor import restrictedpcisscanner
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import RestrictedPCIDevices


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
        json_mock = mock.Mock()
        result_model_mock = mock.Mock()
        get_restricted_pcis_offline = mock.Mock()

        monkeypatch.setattr(
            restrictedpcisscanner.urllib3,
            "PoolManager",
            value=pool_manager_mock,
        )
        monkeypatch.setattr(
            restrictedpcisscanner.json,
            "loads",
            value=json_mock,
        )
        monkeypatch.setattr(
            restrictedpcisscanner,
            "RestrictedPCIDevices",
            value=result_model_mock,
        )
        monkeypatch.setattr(
            restrictedpcisscanner,
            "get_restricted_pcis_offline",
            value=result_model_mock,
        )

        restrictedpcisscanner.produce_restricted_pcis()

        pool_manager_mock.assert_called_once()
        result_model_mock.assert_called_once()
        get_restricted_pcis_offline.assert_not_called()
        assert json_mock.call_count == 2
    else:
        restrictedpcisscanner.produce_restricted_pcis()
        assert len(api.produce.model_instances) == 1
        assert isinstance(api.produce.model_instances[0], RestrictedPCIDevices)
        assert api.produce.model_instances[0].driver_names["devices"]
        assert api.produce.model_instances[0].pci_ids["devices"]


@pytest.mark.skip(reason="Use only for updating the local data")
def test_update_local_data(monkeypatch):
    import urllib3  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(
        api,
        "current_actor",
        CurrentActorMocked(),
    )
    http = urllib3.PoolManager()
    restrictedpcisscanner.get_restricted_pcis(http, update_local_data=True)
