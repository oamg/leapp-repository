from leapp.models import Model, fields
from leapp.topics import SystemFactsTopic


class KernelModuleParameter(Model):
    topic = SystemFactsTopic

    name = fields.String()
    value = fields.String()


class ActiveKernelModule(Model):
    topic = SystemFactsTopic

    filename = fields.String()
    parameters = fields.List(fields.Model(KernelModuleParameter))
    signature = fields.Nullable(fields.String())


class ActiveKernelModulesFacts(Model):
    topic = SystemFactsTopic

    kernel_modules = fields.List(fields.Model(ActiveKernelModule))
