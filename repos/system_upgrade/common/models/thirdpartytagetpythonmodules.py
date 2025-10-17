from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class ThirdPartyTargetPythonModules(Model):
    """
    Information about third-party target Python modules found on system.

    """
    topic = SystemInfoTopic

    target_python = fields.String()
    """
    Target system Python version.
    """

    third_party_modules = fields.List(fields.String(), default=[])
    """
    List of third-party target Python modules found on the source system. Empty list if no modules found.
    """

    third_party_rpm_names = fields.List(fields.String(), default=[])
    """
    List of third-party RPMs found on the source system. Empty list if no modules found.
    """
