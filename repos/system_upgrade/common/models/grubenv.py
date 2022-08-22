from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class HybridImage(Model):
    """
    Model used for instructing Leapp to convert "grubenv" symlink
    into a regular file in case of hybrid (BIOS/EFI) images using BIOS
    on Azure.
    """
    topic = SystemFactsTopic
    detected = fields.Boolean(default=False)
