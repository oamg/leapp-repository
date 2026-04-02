from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class PulseAudioConfiguration(Model):
    """
    Model describing the state of PulseAudio configuration on the system.
    """
    topic = SystemInfoTopic

    modified_defaults = fields.List(fields.String(), default=[])
    """
    Default config files modified from RPM originals (full paths)
    """

    dropin_dirs = fields.List(fields.String(), default=[])
    """
    Drop-in directories that exist and contain files (full paths)
    """

    user_config_dirs = fields.List(fields.String(), default=[])
    """
    Per-user config directories that exist and contain files (full paths)
    """
