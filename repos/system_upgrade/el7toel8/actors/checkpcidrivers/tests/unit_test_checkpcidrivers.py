import itertools
import logging
from functools import partial

import pytest

from leapp import reporting
from leapp.libraries.actor.checkpcidrivers import checkpcidrivers_main, create_dict_lookup, render_report
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import fields, Model, PCIDevice, PCIDevices, RestrictedPCIDevice, RestrictedPCIDevices
from leapp.topics.systeminfo import SystemInfoTopic

logger = logging.getLogger(__name__)

pci_devices = PCIDevices(
    devices=[
        PCIDevice(
            slot="00:00.0",
            driver="",
            dev_cls="Host bridge",
            vendor="Intel Corporation",
            name="440FX - 82441FX PMC [Natoma]",
            subsystem_vendor="Red Hat, Inc.",
            subsystem_name="Qemu virtual machine",
            pci_id="",
            rev="02",
        ),
        PCIDevice(
            slot="00:01.0",
            dev_cls="ISA bridge",
            vendor="Intel Corporation",
            name="82371SB PIIX3 ISA [Natoma/Triton II]",
            subsystem_vendor="Red Hat, Inc.",
            pci_id="15b560:0739",
            subsystem_name="Qemu virtual machine",
        ),
        PCIDevice(
            slot="00:01.1",
            dev_cls="IDE interface",
            vendor="Intel Corporation",
            name="82371SB PIIX3 IDE [Natoma/Triton II]",
            subsystem_vendor="Red Hat, Inc.",
            subsystem_name="Qemu virtual machine",
            pci_id="15b560:0739",
            progif="80",
        ),
    ]
)

restricted_pci_devices = RestrictedPCIDevices(
    driver_names=[
        RestrictedPCIDevice(
            pci_id="nan",
            driver_name="3w-9xxx",
            device_name="3w-9xxx",
            available_rhel7=1,
            supported_rhel7=1,
            available_rhel8=0,
            supported_rhel8=0,
            available_rhel9=0,
            supported_rhel9=0,
            comment="nan",
        ),
        RestrictedPCIDevice(
            pci_id="nan",
            driver_name="3w-sas",
            device_name="3w-sas",
            available_rhel7=1,
            supported_rhel7=1,
            available_rhel8=1,
            supported_rhel8=0,
            available_rhel9=0,
            supported_rhel9=0,
            comment="nan",
        ),
        RestrictedPCIDevice(
            pci_id="nan",
            driver_name="acard-ahci",
            device_name="acard-ahci",
            available_rhel7=1,
            supported_rhel7=1,
            available_rhel8=1,
            supported_rhel8=1,
            available_rhel9=0,
            supported_rhel9=0,
            comment="nan",
        ),
    ],
    pci_ids=[
        RestrictedPCIDevice(
            pci_id="0x1000:0x0060",
            driver_name="megaraid_sas",
            device_name="SAS1078R",
            available_rhel7=1,
            supported_rhel7=1,
            available_rhel8=0,
            supported_rhel8=0,
            available_rhel9=0,
            supported_rhel9=0,
            comment="nan",
        ),
        RestrictedPCIDevice(
            pci_id="0x1000:0x0064",
            driver_name="mpt2sas",
            device_name="SAS2116_1",
            available_rhel7=1,
            supported_rhel7=1,
            available_rhel8=1,
            supported_rhel8=0,
            available_rhel9=0,
            supported_rhel9=0,
            comment="nan",
        ),
        RestrictedPCIDevice(
            pci_id="0x1000:0x0065",
            driver_name="mpt2sas",
            device_name="SAS2116_2",
            available_rhel7=1,
            supported_rhel7=1,
            available_rhel8=1,
            supported_rhel8=1,
            available_rhel9=0,
            supported_rhel9=0,
            comment="nan",
        ),
    ],
)


@pytest.mark.parametrize(
    (
        "driver_name",
        "pci_id",
        "inhibit_upgrade",
        "num_msgs",
    ),
    [
        (
            "good driver name",
            "good pci id",
            None,
            0,
        ),
        (
            "3w-9xxx",
            "good pci id",
            True,
            1,
        ),
        (
            "3w-sas",
            "good pci id",
            None,
            1,
        ),
        (
            "acard-ahci",
            "good pci id",
            None,
            0,
        ),
        (
            "good driver name",
            "0x1000:0x0060",
            True,
            1,
        ),
        (
            "good driver name",
            "0x1000:0x0064",
            None,
            1,
        ),
        (
            "good driver name",
            "0x1000:0x0065",
            None,
            0,
        ),
    ],
)
def test_basic_checkpcidrivers(
    monkeypatch,
    driver_name,
    pci_id,
    inhibit_upgrade,
    num_msgs,
):
    """Check the main actor function."""
    pci_devices.devices[0].driver = driver_name
    pci_devices.devices[0].pci_id = pci_id
    monkeypatch.setattr(
        api,
        "current_actor",
        CurrentActorMocked(msgs=[pci_devices, restricted_pci_devices]),
    )
    monkeypatch.setattr(
        reporting,
        "create_report",
        create_report_mocked(),
    )
    monkeypatch.setattr(
        CurrentActorMocked,
        "produce",
        produce_mocked(),
    )
    checkpcidrivers_main()
    if inhibit_upgrade:
        assert len(CurrentActorMocked.produce.model_instances) == 1
        assert CurrentActorMocked.produce.model_instances[0].report[
            "flags"
        ] == ["inhibitor"]
    if num_msgs and not inhibit_upgrade:
        assert (
            "flags" not in CurrentActorMocked.produce.model_instances[0].report
        )
    assert len(CurrentActorMocked.produce.model_instances) == num_msgs


RestrictedPCIDevicePrefilled = partial(
    RestrictedPCIDevice,
    pci_id="",
    driver_name="",
    device_name="",
    comment="",
    available_rhel7=1,
    available_rhel9=0,
    supported_rhel7=1,
    supported_rhel9=0,
)


def get_test_case_for_testing_report(
    devices, available_rhel8, supported_rhel8
):
    return devices, {
        d: RestrictedPCIDevicePrefilled(
            available_rhel8=available_rhel8,
            supported_rhel8=supported_rhel8,
        )
        for d in devices
    }


@pytest.mark.parametrize(
    (
        "restricted_driver_names_on_host",
        "restricted_devices_drivers",
        "restricted_pci_ids_on_host",
        "restricted_devices_pcis",
        "inhibit_upgrade",
        "exp_line_length",
    ),
    [
        get_test_case_for_testing_report(("d1", "d2"), 0, 0)
        + get_test_case_for_testing_report(("p1", "p2"), 0, 0)
        + (True, 15),
        get_test_case_for_testing_report(("d1", "d2"), 1, 0)
        + get_test_case_for_testing_report(("p1", "p2"), 1, 0)
        + (True, 8),
        get_test_case_for_testing_report(("d1", "d2"), 0, 1)
        + get_test_case_for_testing_report(("p1", "p2"), 0, 1)
        + (True, 8),
        get_test_case_for_testing_report(("d1", "d2"), 1, 0)
        + get_test_case_for_testing_report(("p1", "p2"), 0, 1)
        + (True, 9),
    ],
)
def test_render_report(
    monkeypatch,
    restricted_driver_names_on_host,
    restricted_pci_ids_on_host,
    restricted_devices_drivers,
    restricted_devices_pcis,
    inhibit_upgrade,
    exp_line_length,
    caplog,
):
    """Check report appearance."""
    monkeypatch.setattr(
        reporting,
        "create_report",
        create_report_mocked(),
    )
    reporting.create_report(
        render_report(
            restricted_driver_names_on_host=restricted_driver_names_on_host,
            restricted_pci_ids_on_host=restricted_pci_ids_on_host,
            restricted_devices_drivers=restricted_devices_drivers,
            restricted_devices_pcis=restricted_devices_pcis,
            inhibit_upgrade=inhibit_upgrade,
        )
    )
    logger.info(reporting.create_report.report_fields["summary"])
    assert sum(len(m.split("\n")) for m in caplog.messages) == exp_line_length


class M(Model):
    """A model just for the purpose of further test."""

    topic = SystemInfoTopic

    a = fields.Integer(default=0)
    b = fields.Integer(default=0)


@pytest.mark.parametrize(
    ("driver_names", "key", "exp", "exception"),
    [
        # Normal case
        (
            [M(a=1, b=2), M(a=1, b=3)],
            "b",
            {2: M(a=1, b=2), 3: M(a=1, b=3)},
            None,
        ),
        # Not existing attribute
        (
            [M(a=1, b=2), M(a=1, b=3)],
            "c",
            None,
            AttributeError,
        ),
        # Not existing attribute, empty Ms
        (
            [M(), M()],
            "c",
            None,
            AttributeError,
        ),
        # Duplicated attribute values
        (
            [M(a=1, b=2), M(a=1, b=2)],
            "b",
            None,
            ValueError,
        ),
    ],
)
def test_create_dict_lookup_fn(driver_names, key, exp, exception):
    if exception:
        with pytest.raises(exception):
            create_dict_lookup(driver_names, key)
    else:
        assert create_dict_lookup(driver_names, key) == exp


def test_checkpcidrivers_no_restricted_devs(current_actor_context):
    """Test if actor works well when no messages provided."""
    current_actor_context.run()
    assert current_actor_context._messaging.errors()
