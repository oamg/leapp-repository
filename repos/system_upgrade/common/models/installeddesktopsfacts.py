from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class InstalledDesktopsFacts(Model):
    """
    The model includes fact about installed
    """
    topic = SystemFactsTopic
    gnome_installed = fields.Boolean(default=False)
    kde_installed = fields.Boolean(default=False)
