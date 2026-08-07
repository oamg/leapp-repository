from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class FirmwareFacts(Model):
    topic = SystemFactsTopic

    firmware = fields.StringEnum(['bios', 'efi'])
    """ System firmware interface (BIOS or EFI) """

    ppc64le_opal = fields.Nullable(fields.Boolean())
    """ Check OPAL presence to identify ppc64le bare metal systems """

    secureboot_enabled = fields.Nullable(fields.Boolean())
    """
    Check whether SecureBoot is enabled, always False on BIOS systems

    Note that some machines do not support SecureBoot at all - even for systems booted with UEFI.
    For systems booted with UEFI that does not support SecureBoot set None.
    """

    efi_vars_accessible = fields.Nullable(fields.Boolean())
    """
    Whether EFI runtime variables are accessible.

    True when mokutil can query EFI vars (even if SecureBoot is unsupported).
    False when mokutil fails with "EFI variables are not supported".
    None for BIOS systems or when mokutil is not installed.
    """
