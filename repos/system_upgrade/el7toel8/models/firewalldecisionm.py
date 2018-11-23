from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class FirewallDecisionM(Model):
    topic = SystemInfoTopic

    # Yes, No, Skip
    disable_choice = fields.StringEnum(choices=['Y', 'N', 'S'])

