from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class MachineIdInfo(Model):
    """
    Information about /etc/machine-id on the source system.
    """
    topic = SystemInfoTopic

    machine_id = fields.Nullable(fields.String())
    """
    Content of /etc/machine-id (trailing newline stripped), or None if missing/unreadable.
    """
