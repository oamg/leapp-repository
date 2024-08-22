from leapp.models import Model
from leapp.topics import SystemFactsTopic


class ConvertGrubenvTask(Model):
    """
    Model used for instructing Leapp to convert "grubenv" symlink into a
    regular file.
    """

    topic = SystemFactsTopic
