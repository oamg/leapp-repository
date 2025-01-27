from leapp.models import EFIBootEntry, fields, Model
from leapp.topics import SystemInfoTopic


class ArmWorkaroundEFIBootloaderInfo(Model):
    """
    Information about an Upgrade UEFI boot loader entry.
    """

    topic = SystemInfoTopic

    original_entry = fields.Model(EFIBootEntry)

    upgrade_entry = fields.Model(EFIBootEntry)

    upgrade_bls_dir = fields.String()
    """
    Path to custom BLS dir used by the upgrade EFI bootloader

    The path is absolute w.r.t. '/'. The actual value of the 'blsdir' variable
    that is set in the upgrade grubenv will be relative to '/boot/'.
    """

    upgrade_entry_efi_path = fields.String()
    """
    Full path to the folder containing EFI binaries for the upgrade entry.

    Example:
        /boot/efi/EFI/leapp
    """
