from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class InstalledKdeAppsFacts(Model):
    topic = SystemFactsTopic
    installed_apps = fields.List(fields.String(), default=[])
