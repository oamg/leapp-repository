from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class MultipathInfo(Model):
    """ Available information about multpath devices of the source system. """
    topic = SystemInfoTopic

    is_configured = fields.Boolean(default=False)
    """
    True if multipath is configured on the system.

    Detected based on checking whether /etc/multipath.conf exists.
    """

    config_dir = fields.Nullable(fields.String())
    """ Value of config_dir in the defaults section. None if not set. """


class UpdatedMultipathConfig(Model):
    """ Information about multipath config that needed to be modified for the target system. """
    topic = SystemInfoTopic

    updated_config_location = fields.String()
    """ Location of the updated config that should be propagated to the source system. """

    target_path = fields.String()
    """ Location where should be the updated config placed. """


class MultipathConfigUpdatesInfo(Model):
    """ Aggregate information about multipath configs that were updated. """
    topic = SystemInfoTopic

    updates = fields.List(fields.Model(UpdatedMultipathConfig), default=[])
    """ Collection of multipath config updates that must be performed during the upgrade. """


class MultipathConfig8to9(Model):
    """
    Model information about multipath configuration file important for the 8>9 upgrade path.

    Note: This model is in the common repository due to the technical reasons
          (reusing parser code in a single actor), and it should not be emitted on
          non-8to9 upgrade paths. In the future, this model will likely be moved into
          el8toel9 repository.
    """
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
    """
    Model representing information from multipath configuration files important for the 8>9 upgrade path.

    Note: This model is in the common repository due to the technical reasons
          (reusing parser code in a single actor), and it should not be emitted on
          non-8to9 upgrade paths. In the future, this model will likely be moved into
          el8toel9 repository.
    """
    topic = SystemInfoTopic

    configs = fields.List(fields.Model(MultipathConfig8to9), default=[])
    """List of multipath configuration files"""
