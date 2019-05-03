from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class OpenSshPermitRootLogin(Model):
    topic = SystemInfoTopic

    value = fields.StringEnum(['yes', 'prohibit-password',
                               'forced-commands-only', 'no'])
    in_match = fields.Nullable(fields.List(fields.String()))


class OpenSshConfig(Model):
    """
    OpenSSH server configuration.

    This model contains the first effective configuration option specified
    in the configuration file or a list of all the options specified
    in all the conditional blocks used throughout the file.
    """
    topic = SystemInfoTopic

    permit_root_login = fields.List(fields.Model(OpenSshPermitRootLogin))
    use_privilege_separation = fields.Nullable(fields.StringEnum(['sandbox',
                                                                  'yes',
                                                                  'no']))
    protocol = fields.Nullable(fields.String())
    ciphers = fields.Nullable(fields.String())
    macs = fields.Nullable(fields.String())

    modified = fields.Nullable(fields.Boolean())
