from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class KernelCmdlineArg(Model):
    """
    Single kernel command line parameter with/without a value

    When produced alone, represents a parameter to include in RHEL-8 kernel cmdline.
    """
    topic = SystemInfoTopic

    key = fields.String()
    value = fields.Nullable(fields.String())


class TargetKernelCmdlineArgTasks(Model):
    """
    Desired modifications of the target kernel args
    """
    topic = SystemInfoTopic

    to_add = fields.List(fields.Model(KernelCmdlineArg), default=[])
    to_remove = fields.List(fields.Model(KernelCmdlineArg), default=[])


class KernelCmdline(Model):
    """
    Kernel command line parameters the system was booted with
    """
    topic = SystemInfoTopic

    parameters = fields.List(fields.Model(KernelCmdlineArg))
