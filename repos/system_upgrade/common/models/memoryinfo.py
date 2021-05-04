from leapp.models import Model, fields
from leapp.topics import SystemFactsTopic


class MemoryInfo(Model):
    """
    Represents information about available memory (KiB)
    """

    topic = SystemFactsTopic

    mem_total = fields.Nullable(fields.Integer())
    """
    Total memory in KiB
    """
