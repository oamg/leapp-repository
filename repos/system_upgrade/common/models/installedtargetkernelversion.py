from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class InstalledTargetKernelVersion(Model):
    """
    This message is used to propagate the version of the kernel that has been installed during the upgrade process.

    The version value is mainly used for boot loader entry manipulations, to know which boot entry to manipulate.
    """
    topic = SystemInfoTopic
    version = fields.String()
