from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class VsftpdConfig(Model):
    """
    Model representing some aspects of a vsftpd configuration file.

    The attributes representing the state of configuration options are nullable, so that
    they can represent the real state of the option in the file: if an option is set to "YES"
    in the configuration file, the corresponding attribute is set to True; if the option
    is set to NO, the attribute is set to False; if the option is not present in the config
    file at all, the attribute is set to None.
    """
    topic = SystemInfoTopic

    path = fields.String()
    """Path to the vsftpd configuration file"""
    strict_ssl_read_eof = fields.Nullable(fields.Boolean())
    """Represents the state of the strict_ssl_read_eof option in the config file"""
    tcp_wrappers = fields.Nullable(fields.Boolean())
    """Represents the state of the tcp_wrappers option in the config file"""


class VsftpdFacts(Model):
    topic = SystemInfoTopic

    default_config_hash = fields.Nullable(fields.String())
    """SHA1 hash of the /etc/vsftpd/vsftpd.conf file, if it exists, None otherwise"""
    configs = fields.List(fields.Model(VsftpdConfig))
    """List of vsftpd configuration files"""
