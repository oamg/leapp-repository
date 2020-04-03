from leapp.models import Model, fields
from leapp.topics import SystemFactsTopic


class IpaInfo(Model):
    topic = SystemFactsTopic

    has_client_package = fields.Boolean()
    is_client_configured = fields.Boolean()

    has_server_package = fields.Boolean()
    is_server_configured = fields.Boolean()
