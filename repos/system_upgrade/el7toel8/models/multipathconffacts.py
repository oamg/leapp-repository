from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class MultipathConfigOption(Model):
    """Model representing information about a multipath configuration option"""
    topic = SystemInfoTopic

    name = fields.String(default='')
    value = fields.String(default='')


class MultipathConfig(Model):
    """Model representing information about a multipath configuration file"""
    topic = SystemInfoTopic

    pathname = fields.String()
    """Config file path name"""

    default_path_checker = fields.Nullable(fields.String())
    config_dir = fields.Nullable(fields.String())
    """Values of path_checker and config_dir in the defaults section.
       None if not set"""

    default_retain_hwhandler = fields.Nullable(fields.Boolean())
    default_detect_prio = fields.Nullable(fields.Boolean())
    default_detect_checker = fields.Nullable(fields.Boolean())
    reassign_maps = fields.Nullable(fields.Boolean())
    """True if retain_attached_hw_handler, detect_prio, detect_path_checker,
       or reassign_maps is set to "yes" in the defaults section. False
       if set to "no". None if not set."""

    hw_str_match_exists = fields.Boolean(default=False)
    ignore_new_boot_devs_exists = fields.Boolean(default=False)
    new_bindings_in_boot_exists = fields.Boolean(default=False)
    unpriv_sgio_exists = fields.Boolean(default=False)
    detect_path_checker_exists = fields.Boolean(default=False)
    overrides_hwhandler_exists = fields.Boolean(default=False)
    overrides_pg_timeout_exists = fields.Boolean(default=False)
    queue_if_no_path_exists = fields.Boolean(default=False)
    all_devs_section_exists = fields.Boolean(default=False)
    """True if hw_str_match, ignore_new_boot_devs, new_bindings_in_boot,
       detect_path_checker, or unpriv_sgio is set in any section,
       if queue_if_no_path is included in the features line in any
       section or if hardware_handler or pg_timeout is set in the
       overrides section. False otherwise"""

    all_devs_options = fields.List(fields.Model(MultipathConfigOption),
                                   default=[])
    """options in an all_devs device configuration section to be converted to
       an overrides section"""


class MultipathConfFacts(Model):
    """Model representing information from multipath configuration files"""
    topic = SystemInfoTopic

    configs = fields.List(fields.Model(MultipathConfig), default=[])
    """List of multipath configuration files"""
