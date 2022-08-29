from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class DNFPluginTask(Model):
    """
    Represents information what should DNF do with a specific DNF plugin
    in various stages.

    Currently, it's possible just to disable specified DNF plugins.

    Available stages: "check", "download" and "upgrade
    """

    topic = SystemInfoTopic

    name = fields.String()
    disable_in = fields.List(fields.String(), default=['check', 'download', 'upgrade'])
