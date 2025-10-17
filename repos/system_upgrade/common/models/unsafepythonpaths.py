from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class UnsafePythonPaths(Model):
    """
    Information about third-party Python modules found on system.

    These modules may interfere with the upgrade process or introduce unexpected
    behavior during runtime or after reboot.
    """
    topic = SystemInfoTopic

    is_third_party_module_present = fields.Boolean(default=False)
    """
    True if third-party Python modules are present on the system, indicating inhibition of upgrade.
    """

    third_party_rpm_names = fields.List(fields.String(), default=[])
    """
    List of names of RPMs that own third-party Python modules. Empty list if no modules found.
    """
