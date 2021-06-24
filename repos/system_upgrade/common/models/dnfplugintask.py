from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class DNFPluginTask(Model):
    """
    Represents information what should DNF do with a specifiec DNF plugin
    in various stages.

    Currently, it's possible just to disable specified DNF plugins.

    Available stages: "check", "download" and "upgrade
    """

    topic = SystemInfoTopic

    name = fields.String()
    disable_in = fields.List(fields.String(), default=['check', 'download', 'upgrade'])
