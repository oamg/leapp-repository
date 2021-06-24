from leapp.models import Model, fields
from leapp.topics import SystemFactsTopic


class InstalledDesktopsFacts(Model):
    """
    The model includes fact about installe
    """
    topic = SystemFactsTopic
    gnome_installed = fields.Boolean(default=False)
    kde_installed = fields.Boolean(default=False)
