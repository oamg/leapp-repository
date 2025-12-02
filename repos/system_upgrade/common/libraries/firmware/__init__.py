from leapp.libraries.stdlib import api
from leapp.models import FirmwareFacts


def is_efi():
    """
    Check whether system is booted into BIOS
    """

    ff = next(api.consume(FirmwareFacts), None)
    return ff and ff.firmware == 'efi'


def is_bios():
    """
    Check whether system is booted into BIOS
    """

    ff = next(api.consume(FirmwareFacts), None)
    return ff and ff.firmware == 'bios'
