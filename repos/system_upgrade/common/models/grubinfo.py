from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class GrubInfo(Model):
    """
    Information about Grub
    """
    topic = SystemFactsTopic

    orig_device_name = fields.Nullable(fields.String())
    """
    Original name of the block device where Grub is located.

    The name is persistent during the boot of the system so it's safe to be used during
    preupgrade phases. However the name could be different after the reboot, so
    it's recommended to use `leapp.libraries.common.grub.get_grub_device()` anywhere
    else.
    """
