from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class GrubCfgBios(Model):
    """
    A message providing info about BIOS (non-EFI) GRUB config
    """
    topic = SystemFactsTopic

    insmod_bls = fields.Boolean()
    """ Inform whether blscfg is loaded """
