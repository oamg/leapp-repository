from leapp.models import EFIBootEntry, fields, Model
from leapp.topics import SystemInfoTopic


class ArmWorkaroundEFIBootloaderInfo(Model):
    """
    Information about an Upgrade UEFI boot loader entry.
    """

    topic = SystemInfoTopic

    original_entry = fields.Model(EFIBootEntry)

    upgrade_entry = fields.Model(EFIBootEntry)
