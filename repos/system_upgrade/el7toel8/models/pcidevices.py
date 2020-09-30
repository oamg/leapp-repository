from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class PCIDevice(Model):
    """Model for storing the data of the PCI device.

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
