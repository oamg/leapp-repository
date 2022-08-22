from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class User(Model):
    topic = SystemFactsTopic

    name = fields.String()
    uid = fields.Integer()
    gid = fields.Integer()
    home = fields.String()


class UsersFacts(Model):
    topic = SystemFactsTopic

    users = fields.List(fields.Model(User))
