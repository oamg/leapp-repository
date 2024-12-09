from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class XFSInfo(Model):
    """
    A message containing the parsed results from `xfs_info` command for given mountpoint.

    Attributes are stored as key-value pairs. Optional section attribute is
    stored under the identifier 'specifier'.
    """
    topic = SystemInfoTopic

    mountpoint = fields.String()
    """
    Mountpoint containing the XFS filesystem.
    """

    meta_data = fields.StringMap(fields.String())
    """
    Attributes of 'meta-data' section.
    """

    data = fields.StringMap(fields.String())
    """
    Attributes of 'data' section.
    """

    naming = fields.StringMap(fields.String())
    """
    Attributes of 'naming' section.
    """

    log = fields.StringMap(fields.String())
    """
    Attributes of 'log' section.
    """

    realtime = fields.StringMap(fields.String())
    """
    Attributes of 'realtime' section.
    """


class XFSInfoFacts(Model):
    """
    Message containing the xfs info for all mounted XFS filesystems.
    """
    topic = SystemInfoTopic

    mountpoints = fields.List(fields.Model(XFSInfo))
