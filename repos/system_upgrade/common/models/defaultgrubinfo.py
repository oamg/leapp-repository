from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class DefaultGrub(Model):
    """
    A model with '/etc/default/grub' option as key / value
    """
    topic = SystemFactsTopic

    name = fields.String()
    """ Option name, e.g. GRUB_TIMEOUT """
    value = fields.String()
    """ Option value, e.g. '5' in case of GRUB_TIMEOUT=5 """


class DefaultGrubInfo(Model):
    """
    A message with '/etc/default/grub' content
    """

    topic = SystemFactsTopic

    default_grub_info = fields.List(fields.Model(DefaultGrub))
    """ List of '/etc/default/grub' options as key / value """
