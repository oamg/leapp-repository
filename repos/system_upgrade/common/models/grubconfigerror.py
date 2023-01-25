from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class GrubConfigError(Model):
    ERROR_CORRUPTED_GRUBENV = 'corrupted grubenv'
    ERROR_MISSING_NEWLINE = 'missing newline'
    ERROR_GRUB_CMDLINE_LINUX_SYNTAX = 'GRUB_CMDLINE_LINUX syntax'

    topic = SystemFactsTopic

    # XXX FIXME(ivasilev) Rename to error_resolvable?
    # If error can be automatically resolved (ex. in addupgradebootentry actor)
    error_detected = fields.Boolean(default=False)
    error_type = fields.StringEnum([ERROR_CORRUPTED_GRUBENV, ERROR_MISSING_NEWLINE, ERROR_GRUB_CMDLINE_LINUX_SYNTAX])
    # Paths to config files
    files = fields.List(fields.String())
