from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class Module(Model):
    """
    A single DNF module identified by its name and stream.
    """
    topic = SystemFactsTopic
    name = fields.String()
    stream = fields.String()


class EnabledModules(Model):
    """
    DNF modules enabled on the source system.
    """
    topic = SystemFactsTopic

    modules = fields.List(fields.Model(Module), default=[])
