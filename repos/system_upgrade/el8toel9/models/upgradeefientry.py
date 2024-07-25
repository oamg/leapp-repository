from leapp.models import fields, EFIBootEntry
from leapp.topics import SystemInfoTopic


class UpgradeEFIBootEntry(EFIBootEntry):
    """
    Information about an Upgrade UEFI boot loader entry.
    """
