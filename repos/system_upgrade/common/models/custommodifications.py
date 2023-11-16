from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class CustomModifications(Model):
    """Model to store any custom or modified files that are discovered in leapp directories"""
    topic = SystemFactsTopic

    filename = fields.String()
    actor_name = fields.String()
    type = fields.StringEnum(choices=['custom', 'modified'])
    rpm_checks_str = fields.String(default='')
    component = fields.String()
