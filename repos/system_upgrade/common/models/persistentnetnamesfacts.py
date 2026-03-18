from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic
from leapp.utils.deprecation import deprecated


class PCIAddress(Model):
    """
    Network Interface PCI address.

    This model should not be produced nor consumed by actors directly.
    It's part of the Interface model.
    """
    topic = SystemInfoTopic

    domain = fields.String()
    bus = fields.String()
    function = fields.String()
    device = fields.String()


class Interface(Model):
    """
    Physical network interface

    Contains information about a network interface collected from udev.
    Data can be incomplete in case of issues or when the interface is not
    managed by udev.

    This model should not be produced or consumed by actors directly.
    See PersistentNetNamesFacts or PersistentNetNamesFactsInitramfs.
    """
    topic = SystemInfoTopic

    name = fields.String()
    """
    Name of the interface.
    """

    devpath = fields.String()
    """
    Path to the device.
    """

    driver = fields.String()
    """
    Network interface driver identifier.
    """

    vendor = fields.String()
    """
    Numeric identifier of the hardware vendor on PCI bus.
    """

    pci_info = fields.Nullable(fields.Model(PCIAddress))
    """
    Parsed PCI address of the network interface.

    The value is None if the network interface is not connected via PCI or it is not managed
    by udev.
    """

    mac = fields.String()
    """
    MAC address of the network interface.
    """


class PersistentNetNamesFacts(Model):
    """
    Information about network interfaces gather from the original system
    """
    topic = SystemInfoTopic
    interfaces = fields.List(fields.Model(Interface))
    """
    List of network interfaces with information collected from udev.
    """


class PersistentNetNamesFactsInitramfs(PersistentNetNamesFacts):
    """
    Information about network interfaces gather from initramfs with the kernel of target system
    """
    pass


@deprecated(
    since="2026-03-18",
    message=(
        "Information provided in this message is not always complete and it's"
        " not used nowadays when net naming scheme is set during the upgrade."
    )
)
class RenamedInterface(Model):
    """
    Provide original and new name of the network interface when renamed
    """
    topic = SystemInfoTopic

    original_name = fields.String()
    """
    Original interface name.
    """

    new_name = fields.String()
    """
    New interface name.
    """


@deprecated(
    since="2026-03-18",
    message=(
        "Information provided in this message is not always complete and it's"
        " not used nowadays when net naming scheme is set during the upgrade."
    )
)
class RenamedInterfaces(Model):
    """
    Provide list of renamed network interfaces

    These interfaces will use different names on the target system
    in comparison with original names.
    """
    topic = SystemInfoTopic

    renamed = fields.List(fields.Model(RenamedInterface))
    """
    The list of renamed interfaces.
    """
