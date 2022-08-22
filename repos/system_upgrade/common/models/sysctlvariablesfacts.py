from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class SysctlVariable(Model):
    topic = SystemFactsTopic

    name = fields.String()
    value = fields.String()


class SysctlVariablesFacts(Model):
    topic = SystemFactsTopic

    sysctl_variables = fields.List(fields.Model(SysctlVariable))
