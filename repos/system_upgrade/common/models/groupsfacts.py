from leapp.models import Model, fields
from leapp.topics import SystemFactsTopic


class Group(Model):
    topic = SystemFactsTopic

    name = fields.String()
    gid = fields.Integer()
    members = fields.List(fields.String())


class GroupsFacts(Model):
    topic = SystemFactsTopic

    groups = fields.List(fields.Model(Group))
