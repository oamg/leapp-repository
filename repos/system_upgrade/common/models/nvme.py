from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class NVMEDevice(Model):
    """
    Provide information about particular detected NVMe device.

    This model is not expected to be produced or consumed by any actors as
    a standalone message. It is always part of NVMEInfo message.
    """

    topic = SystemInfoTopic
    sys_class_path = fields.String()
    """
    Path to the NVMe device used for the detection.

    Usually: "/sys/class/nvme/<dev-name>".
    """

    name = fields.String()
    """
    The NVMe device name.
    """

    transport = fields.String()
    """
    The NVMe transport type of the NVMe device.

    Expected usual values:
        * pcie
        * tcp
        * rdma
        * fc

    NOTE: Based on the used kernel, additional values are possible and in future
    the list could be even extended. As just specific values are important for
    us, I am keeping it as a string to allow any possible value that appears.
    """


class NVMEInfo(Model):
    """
    Provide basic information about detected NVMe devices and setup.

    Contains information just in scope required for the proper handling during
    the IPU.
    """

    topic = SystemInfoTopic
    devices = fields.List(fields.Model(NVMEDevice), default=[])
    """
    List of detected NVMe devices.
    """

    hostnqn = fields.Nullable(fields.String())
    """
    Human-readable host identifier in NVMe Qualified Name format

    Alias NVMe-oF host NQN. It's mandatory for RDMA, FC, and TCP transport
    types, but optional for PCIe. If not defined, the value is None
    """

    hostid = fields.Nullable(fields.String())
    """
    Persistent UUID for the NVMe host.

    Alias NVMe-oF host NQN. It's mandatory for RDMA, FC, and TCP transport
    types, but optional for PCIe. If not defined, the value is None
    """
