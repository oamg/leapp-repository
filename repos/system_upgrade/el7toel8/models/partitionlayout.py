from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class PartitionInfo(Model):
    """
    Information about a single partition.
    """
    topic = SystemInfoTopic

    part_device = fields.String()
    """ Partition device """

    start_offset = fields.Integer()
    """ Partition start - offset from the start of the block device in bytes """


class GRUBDevicePartitionLayout(Model):
    """
    Information about partition layout of a GRUB device.
    """
    topic = SystemInfoTopic

    device = fields.String()
    """ GRUB device """

    partitions = fields.List(fields.Model(PartitionInfo))
    """ List of partitions present on the device """
