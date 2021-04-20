"""
TODOs:
1. consider the idea to compare data sources timestamp in order to decide
   if the source is actual or not
"""

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import PCIDevices, RestrictedPCIDevices
from leapp.reporting import create_report


def render_report(
    restricted_driver_names_on_host,
    restricted_pci_ids_on_host,
    restricted_devices_drivers,
    restricted_devices_pcis,
    inhibit_upgrade=False,
):
    """
    Render the report for restricted PCI devices in use.

    :param inhibit_upgrade: if True, the report will have Inhibitor flag and
        the upgrade will be inhibited.
    """
    # Prefilter needed data for the report
    unavailable_driver_names = tuple(
        driver
        for driver in restricted_driver_names_on_host
        if restricted_devices_drivers[driver].available_rhel8 == 0
    )
    unavailable_pci_ids = tuple(
        pci_id
        for pci_id in restricted_pci_ids_on_host
        if restricted_devices_pcis[pci_id].available_rhel8 == 0
    )
    unsupported_driver_names = tuple(
        driver
        for driver in restricted_driver_names_on_host
        if restricted_devices_drivers[driver].supported_rhel8 == 0
    )
    unsupported_pci_ids = tuple(
        pci_id
        for pci_id in restricted_pci_ids_on_host
        if restricted_devices_pcis[pci_id].supported_rhel8 == 0
    )

    # Render the report entities
    title = "Detected PCI drivers that are restricted on RHEL8."

    # Prepare summary
    summary_partial = "The following drivers are restricted on RHEL 8 system:"
    resources = []
    # Process unavailable devices
    if unavailable_driver_names or unavailable_pci_ids:
        summary_partial += "\n\t Unavailable in RHEL8:"
        if unavailable_driver_names:
            summary_partial += "\n\t\t- driver names:\n"
            summary_partial += "\t\t\t- " + "\n\t\t\t- ".join(
                unavailable_driver_names
            )
            resources += [reporting.RelatedResource('kernel-driver', i) for i in unavailable_driver_names]
        if unavailable_pci_ids:
            summary_partial += "\n\t\t- pci ids:\n"
            summary_partial += "\t\t\t- " + "\n\t\t\t- ".join(
                unavailable_pci_ids
            )

    # Process unsupported devices
    if unsupported_driver_names or unsupported_pci_ids:
        summary_partial += "\n\t Unsupported in RHEL8:"
        if unsupported_driver_names:
            summary_partial += "\n\t\t- driver names:\n"
            summary_partial += "\t\t\t- " + "\n\t\t\t- ".join(
                unsupported_driver_names
            )
            resources += [reporting.RelatedResource('kernel-driver', i) for i in unsupported_driver_names]
        if unsupported_pci_ids:
            summary_partial += "\n\t\t- pci ids:\n"
            summary_partial += "\t\t\t- " + "\n\t\t\t- ".join(
                unsupported_pci_ids
            )

    reports = [
        reporting.Title(title),
        reporting.Summary(summary_partial),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Tags([reporting.Tags.KERNEL, reporting.Tags.DRIVERS]),
    ]

    if resources:
        reports += resources
    if inhibit_upgrade:
        reports += [reporting.Flags([reporting.Flags.INHIBITOR])]
    return reports


def create_dict_lookup(driver_names, key):
    """
    Creates a dict lookup from the list of Models.

    :param driver_names: List[leapp.models.Model[K, V]]
    :param key: a key value, that will be used as a primary key to generate a
        result Dict
    :return: Dict[leapp.models.Model[K,V].key, leapp.models.Model[K,V]]
    :raises ValueError: if there are duplicates of leapp.models.Model[K,V].key
    :raises AttributeError: if key not in K (Model attributes)

    Example:
    >>> create_dict_lookup([Model(a=1, b=2), Model(a=2, b=3)], key="b") == {
    >>>     2: Model(a=1, b=2),
    >>>     3: Model(a=2, b=3),
    >>> }
    """
    lookup = {getattr(item, key): item for item in driver_names}
    if len(lookup) != len(driver_names):
        raise ValueError("A duplicated key(s) found")
    return lookup


def checkpcidrivers_main():
    """Main entrypoint of the CheckPCIDrivers Actor."""
    try:
        pci_devs = next(api.consume(PCIDevices))
        restricted_pci_devs = next(api.consume(RestrictedPCIDevices))
    except StopIteration:
        raise StopActorExecutionError(
            message=(
                "At least one of the needed messages is empty. "
                "Required messages are PCIDevices, RestrictedPCIDevices."
            )
        )
    else:
        # get set of drivers-names/pci-ids presented on host
        driver_names_on_host = set(dev.driver for dev in pci_devs.devices)
        pci_ids_on_host = set(dev.pci_id for dev in pci_devs.devices)

        # get restricted driver_names and pci_ids dict lookups
        try:
            restricted_devices_drivers = create_dict_lookup(
                restricted_pci_devs.driver_names, key="driver_name"
            )
            restricted_devices_pcis = create_dict_lookup(
                restricted_pci_devs.pci_ids, key="pci_id"
            )
        except (AttributeError, ValueError) as err:
            raise StopActorExecutionError(message=str(err))
        # get set of restricted driver-names/pci-ids presented on host
        restricted_driver_names_on_host = driver_names_on_host & set(
            restricted_devices_drivers
        )
        restricted_pci_ids_on_host = pci_ids_on_host & set(
            restricted_devices_pcis
        )

        # check if at least one driver on host is not available on RHEL8
        if any(
            restricted_devices_drivers[driver_name].available_rhel8 == 0
            for driver_name in restricted_driver_names_on_host
        ) or any(
            restricted_devices_pcis[pci].available_rhel8 == 0
            for pci in restricted_pci_ids_on_host
        ):
            api.current_logger().critical(
                "Some of the host drivers are unavailable on the RHEL 8 "
                "system. Inhibiting the upgrade...",
            )
            create_report(
                render_report(
                    restricted_driver_names_on_host,
                    restricted_pci_ids_on_host,
                    restricted_devices_drivers,
                    restricted_devices_pcis,
                    inhibit_upgrade=True,
                )
            )
        # check if at least one driver on host is not supported on RHEL8
        elif any(
            restricted_devices_drivers[driver_name].supported_rhel8 == 0
            for driver_name in restricted_driver_names_on_host
        ) or any(
            restricted_devices_pcis[pci].supported_rhel8 == 0
            for pci in restricted_pci_ids_on_host
        ):
            api.current_logger().warning(
                "Some of the host drivers are unsupported on the RHEL 8 "
                "system. Warning the user...",
            )
            create_report(
                render_report(
                    restricted_driver_names_on_host,
                    restricted_pci_ids_on_host,
                    restricted_devices_drivers,
                    restricted_devices_pcis,
                )
            )
