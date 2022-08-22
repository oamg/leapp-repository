from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class SELinuxFacts(Model):
    topic = SystemFactsTopic

    runtime_mode = fields.Nullable(fields.StringEnum(['enforcing', 'permissive']))
    static_mode = fields.StringEnum(['enforcing', 'permissive', 'disabled'])
    enabled = fields.Boolean()
    policy = fields.StringEnum(['targeted', 'minimum', 'mls'])
    mls_enabled = fields.Boolean()
