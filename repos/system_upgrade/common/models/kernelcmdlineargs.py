from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class KernelCmdlineArg(Model):
    """
    Single kernel command line parameter with/without a value

    When produced alone, represents a parameter to include in RHEL-8 kernel cmdline.
    """
    topic = SystemInfoTopic

    key = fields.String()
    value = fields.Nullable(fields.String())


class KernelCmdline(Model):
    """
    Kernel command line parameters the system was booted with
    """
    topic = SystemInfoTopic

    parameters = fields.List(fields.Model(KernelCmdlineArg))
