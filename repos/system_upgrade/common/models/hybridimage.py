from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class HybridImageAzure(Model):
    """
    Model used to signify that the system is using a hybrid (BIOS/EFI) images
    using BIOS on Azure.
    """

    topic = SystemFactsTopic
    grubenv_is_symlink_to_efi = fields.Boolean(default=False)
