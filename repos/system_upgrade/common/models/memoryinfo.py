from leapp.models import fields, Model
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
