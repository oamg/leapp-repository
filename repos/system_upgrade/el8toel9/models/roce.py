from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class RoceDetected(Model):
    """
    The model creates a list of
     - RoCE NICs that are detected as connected, which means, they are
       configured persistently
     - RoCE NICs that are in process of connecting (i.e. they are trying
       to get an IP address - and might become connected upon success)
    """
    topic = SystemInfoTopic

    roce_nics_connected = fields.List(fields.String(), default=[])
    """
    List of RoCE NICs which are detected as connected.

    e.g. ["ens1234", "eno3456"]
    """

    roce_nics_connecting = fields.List(fields.String(), default=[])
    """
    List of RoCE NICs which are detected as connecting right now.

    (They might become detected as connected, soon.)
    """
