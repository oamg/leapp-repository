from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class OSReleaseFacts(Model):
    topic = SystemInfoTopic

    id = fields.String()
    name = fields.String()
    pretty_name = fields.String()
    version = fields.String()
    version_id = fields.String()
    variant = fields.Nullable(fields.String()) # isn't specified on some systems
    variant_id = fields.Nullable(fields.String()) # same as above
