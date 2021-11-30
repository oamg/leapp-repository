from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class PCIDevice(Model):
    """
    Model to represent a PCI Device.

    There is the following match between model parameters and
    the fields of the output of a shell command `lspci -vmmk`

    slot - 'Slot',
    dev_cls - 'Class',
    vendor - 'Vendor',
    name - 'Device',
    subsystem_vendor - 'SVendor',
    subsystem_name - 'SDevice',
    physical_slot - 'PhySlot',
    rev - 'Rev',
    progif - 'ProgIf',
    driver - 'Driver',
    modules - 'Module',
    numa_node - 'NUMANode',

    pci_id - represents the numeric identification of the device, formed as
        string concatenating of the numeric device identifiers for fields
        Vendor, Device, SVendor, SDevice (output
        of a shell command `lspci -vmmkn`) with the `:` delimiter.
        For example:
        one device from output of `lspci -vmmkn` is:

        ```
        Slot:	04:00.0
        Class:	0880
        Vendor:	8086
        Device:	15bf
        SVendor:	17aa
        SDevice:	2279
        Rev:	01
        Driver:	thunderbolt
        Module:	thunderbolt
        ```

        then
        pci_id == "8086:15bf:17aa:2279"
    """
    topic = SystemInfoTopic

    slot = fields.String()
    dev_cls = fields.String()
    vendor = fields.String()
    name = fields.String()
    subsystem_vendor = fields.Nullable(fields.String())
    subsystem_name = fields.Nullable(fields.String())
    physical_slot = fields.Nullable(fields.String())
    rev = fields.Nullable(fields.String())
    progif = fields.Nullable(fields.String())
    driver = fields.Nullable(fields.String())
    modules = fields.Nullable(fields.List(fields.String()))
    numa_node = fields.Nullable(fields.String())
    pci_id = fields.String()


class PCIDevices(Model):
    topic = SystemInfoTopic

    devices = fields.List(fields.Model(PCIDevice))


class RestrictedPCIDevice(Model):
    """
    Model to represent known restrictions of the given PCI devices.


    pci_id - unsupported pci_ids. It has the following
        structure: {Vendor}:{Device}:{SVendor}:{SDevice}, where all these 4
        parameters are numeric ids (see shell command spci -vmmkn). If SVendor
        and SDevice fields do not exist, then pci_id has the following structure:
        {Vendor}:{Device}.
    driver_name - the name of restricted driver
    device_name - the name of restricted device
    supported_{rhel_version} - 1 is supported on the given RHEL, 0 - not
        supported
    available_{rhel_version} - 1 is available on the given RHEL, 0 - not
        available. it could be the driver is available, but not supported
    comments - the field for comments
    """
    topic = SystemInfoTopic

    pci_id = fields.Nullable(fields.String())
    driver_name = fields.Nullable(fields.String())
    device_name = fields.Nullable(fields.String())
    available_rhel7 = fields.Integer()
    supported_rhel7 = fields.Integer()
    available_rhel8 = fields.Integer()
    supported_rhel8 = fields.Integer()
    available_rhel9 = fields.Integer()
    supported_rhel9 = fields.Integer()
    comment = fields.Nullable(fields.String())


class RestrictedPCIDevices(Model):
    """
    Model to represent all known restricted PCI devices.

    Restricted devices might be restricted based on either
     - pci id (each particular device)
     - driver name (all the family of the devices being served by the
        particular driver).

    However the data type, which represents how the pci id or driver name is
    restricted is identical.

    Thus both attributes has the same data type.

    driver_names - is a container with the devices, which are restricted by
        the driver name identifier
    pci_ids - is a container with the devices, which are restricted by
        the pci_id identifier
    """
    topic = SystemInfoTopic

    driver_names = fields.List(
        fields.Model(RestrictedPCIDevice),
    )
    pci_ids = fields.List(
        fields.Model(RestrictedPCIDevice),
    )
