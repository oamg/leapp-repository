from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class SelinuxRelabelDecision(Model):
    topic = SystemInfoTopic

    set_relabel = fields.Boolean()


class SelinuxPermissiveDecision(Model):
    topic = SystemInfoTopic

    set_permissive = fields.Boolean()
