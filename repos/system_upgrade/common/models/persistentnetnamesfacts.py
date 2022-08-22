from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class PCIAddress(Model):
    """
    TODO: tbd
    """
    topic = SystemInfoTopic

    domain = fields.String()
    bus = fields.String()
    function = fields.String()
    device = fields.String()


class Interface(Model):
    """
    TODO: tbd - Interface or NetworkInterface?
    """
    topic = SystemInfoTopic

    name = fields.String()
    devpath = fields.String()
    driver = fields.String()
    vendor = fields.String()
    pci_info = fields.Model(PCIAddress)
    mac = fields.String()


class PersistentNetNamesFacts(Model):
    """
    Information about network interfaces gather from the original system
    """
    topic = SystemInfoTopic
    interfaces = fields.List(fields.Model(Interface))


class PersistentNetNamesFactsInitramfs(PersistentNetNamesFacts):
    """
    Information about network interfaces gather from initramfs with the kernel of target system
    """
    pass


class RenamedInterface(Model):
    """
    Provide original and new name of the network interface when renamed
    """
    topic = SystemInfoTopic

    rhel7_name = fields.String()
    rhel8_name = fields.String()


class RenamedInterfaces(Model):
    """
    Provide list of renamed network interfaces

    These interfaces will use different names on the target system
    in comparison with original names.
    """
    topic = SystemInfoTopic

    renamed = fields.List(fields.Model(RenamedInterface))
