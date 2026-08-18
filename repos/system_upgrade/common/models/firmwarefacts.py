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
    Check whether SecureBoot is enabled.

    The value can be None in these cases:
        * on BIOS systems (mokutil is never called)
        * on systems that do not support SecureBoot (even when booted with UEFI)
        * on systems with disabled EFI variables (usually on Real Time systems due to effect on latency)
    """

    efi_vars_accessible = fields.Nullable(fields.Boolean())
    """
    True if EFI runtime variables are accessible via mokutil.

    Checking this value is useful on systems booted with UEFI when the information about
    the Secure Boot settings is not determined (`secureboot_enabled` is None).
    Other values:

        * False if mokutil fails with "EFI variables are not supported".
        * None for BIOS systems or when mokutil is not installed.
    """
