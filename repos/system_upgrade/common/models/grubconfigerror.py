from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class GrubConfigError(Model):
    topic = SystemFactsTopic

    error_detected = fields.Boolean(default=False)
    error_type = fields.StringEnum(['GRUB_CMDLINE_LINUX syntax', 'missing newline'])
