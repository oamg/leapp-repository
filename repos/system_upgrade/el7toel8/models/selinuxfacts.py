from leapp.models import Model, fields
from leapp.topics import SystemFactsTopic


class SELinuxFacts(Model):
    topic = SystemFactsTopic

    # FIXME: fixme properly regarding the issue:
    # # https://github.com/oamg/leapp-repository/issues/20
    runtime_mode = fields.Nullable(fields.StringEnum(['enforcing', 'permissive']))
    static_mode = fields.StringEnum(['enforcing', 'permissive', 'disabled'])
    enabled = fields.Boolean()
    policy = fields.String()
    mls_enabled = fields.Boolean()
