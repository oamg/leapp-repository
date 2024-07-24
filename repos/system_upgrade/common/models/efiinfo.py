from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class EFIBootEntry(Model):
    """
    Information about an UEFI boot loader entry.
    """
    topic = SystemInfoTopic

    boot_number = fields.String()
    """Expected string, e.g. '0001'. """

    label = fields.String()
    """Label of the UEFI entry. E.g. 'Redhat'"""

    active = fields.Boolean()
    """True when the UEFI entry is active (asterisk is present next to the boot number)"""

    efi_bin_source = fields.String()
    """Source of the UEFI binary.

    It could contain various values, e.g.:
        FvVol(7cb8bdc9-f8eb-4f34-aaea-3ee4af6516a1)/FvFile(462caa21-7614-4503-836e-8ab6f4662331)
        HD(1,GPT,28c77f6b-3cd0-4b22-985f-c99903835d79,0x800,0x12c000)/File(\\EFI\\redhat\\shimx64.efi)
        PciRoot(0x0)/Pci(0x2,0x3)/Pci(0x0,0x0)N.....YM....R,Y.
    """
