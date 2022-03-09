from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class OpenSshPermitRootLogin(Model):
    topic = SystemInfoTopic

    value = fields.StringEnum(['yes', 'prohibit-password',
                               'forced-commands-only', 'no'])
    """ Value of a PermitRootLogin directive. """
    in_match = fields.Nullable(fields.List(fields.String()))
    """ Criteria of Match blocks the PermitRootLogin directive occured in, if any. """


class OpenSshConfig(Model):
    """
    OpenSSH server configuration.

    This model contains the first effective configuration option specified
    in the configuration file or a list of all the options specified
    in all the conditional blocks used throughout the file.
    """
    topic = SystemInfoTopic

    permit_root_login = fields.List(fields.Model(OpenSshPermitRootLogin))
    """ All PermitRootLogin directives. """
    use_privilege_separation = fields.Nullable(fields.StringEnum(['sandbox',
                                                                  'yes',
                                                                  'no']))
    """ Value of the UsePrivilegeSeparation directive, if present. Removed in RHEL 8. """
    protocol = fields.Nullable(fields.String())
    """ Value of the Protocols directive, if present. Removed in RHEL 8. """
    ciphers = fields.Nullable(fields.String())
    """ Value of the Ciphers directive, if present. Ciphers separated by comma. """
    macs = fields.Nullable(fields.String())
    """ Value of the MACs directive, if present. """
    deprecated_directives = fields.List(fields.String())
    """ Configuration directives that were deprecated in the new version of openssh. """
    subsystem_sftp = fields.Nullable(fields.String())
    """ The "Subsystem sftp" configuration option, if present """

    modified = fields.Boolean(default=False)
    """ True if the configuration file was modified. """
