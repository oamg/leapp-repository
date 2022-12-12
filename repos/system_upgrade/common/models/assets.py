from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class ConsumedDataAsset(Model):
    """Information about a used data asset."""
    topic = SystemFactsTopic

    filename = fields.String()
    fulltext_name = fields.String()
    docs_url = fields.String()
    docs_title = fields.String()
    provided_data_streams = fields.Nullable(fields.List(fields.String()))
