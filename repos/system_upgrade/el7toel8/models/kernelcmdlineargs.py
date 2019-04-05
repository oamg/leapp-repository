from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class KernelCmdlineArg(Model):
    """
    Single kernel command line argument to include to RHEL-8 kernel cmdline
    """
    topic = SystemInfoTopic

    key = fields.String()
    value = fields.String()
