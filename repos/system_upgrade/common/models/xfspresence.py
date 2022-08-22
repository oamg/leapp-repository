from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class XFSPresence(Model):
    """
    A generic message reporting mountpoints with XFS using ftype = 0
    """
    topic = SystemInfoTopic

    present = fields.Boolean(default=False)
    """ XFS is used on at least one mountpoint """

    without_ftype = fields.Boolean(default=False)
    """ At least one mountpoint is using XFS with ftype=0 """

    mountpoints_without_ftype = fields.List(fields.String(), default=[])
    """ List of mountpoints that have ftype=0 """
