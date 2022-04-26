from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class MultipathConfig8to9(Model):
    """Model representing information about a multipath configuration file"""
    topic = SystemInfoTopic

    pathname = fields.String()
    """Config file path name"""

    config_dir = fields.Nullable(fields.String())
    """Value of config_dir in the defaults section. None if not set"""

    enable_foreign_exists = fields.Boolean(default=False)
    """True if enable_foreign is set in the defaults section"""

    invalid_regexes_exist = fields.Boolean(default=False)
    """True if any regular expressions have the value of "*" """

    allow_usb_exists = fields.Boolean(default=False)
    """True if allow_usb_devices is set in the defaults section."""


class MultipathConfFacts8to9(Model):
    """Model representing information from multipath configuration files"""
    topic = SystemInfoTopic

    configs = fields.List(fields.Model(MultipathConfig8to9), default=[])
    """List of multipath configuration files"""
