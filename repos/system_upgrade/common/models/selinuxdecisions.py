from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class SelinuxRelabelDecision(Model):
    topic = SystemInfoTopic

    set_relabel = fields.Boolean()


class SelinuxPermissiveDecision(Model):
    topic = SystemInfoTopic

    set_permissive = fields.Boolean()
