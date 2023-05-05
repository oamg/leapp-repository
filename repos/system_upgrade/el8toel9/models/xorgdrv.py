from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class XorgDrv(Model):
    """
    Name of the Xorg driver in use and whether it has custom options set.

    This model is not expected to be used as a message (produced/consumed by actors).
    It is used from within the XorgDrvFacts model.
    """
    topic = SystemFactsTopic

    driver = fields.String()
    has_options = fields.Boolean(default=False)


class XorgDrvFacts(Model):
    """
    List of Xorg drivers.
    """
    topic = SystemFactsTopic

    xorg_drivers = fields.List(fields.Model(XorgDrv))
