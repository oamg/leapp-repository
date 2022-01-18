from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class FirmwareFacts(Model):
    topic = SystemFactsTopic

    firmware = fields.StringEnum(['bios', 'efi'])
    """ System firmware interface (BIOS or EFI) """
    ppc64le_opal = fields.Nullable(fields.Boolean())
    """ Check OPAL presence to identify ppc64le bare metal systems """
