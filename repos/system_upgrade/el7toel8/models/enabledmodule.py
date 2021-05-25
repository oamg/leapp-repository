from leapp.models import Model, fields
from leapp.topics import SystemFactsTopic


"""
A single DNF module enabled on the source system.
"""
class EnabledModule(Model):
    topic = SystemFactsTopic
    name = fields.String()
    stream = fields.String()


class EnabledModules(Model):
    topic = SystemFactsTopic
    # modules = fields.List(fields.Model(EnabledModule), default=[])
    modules = fields.List(fields.Model(EnabledModule))
