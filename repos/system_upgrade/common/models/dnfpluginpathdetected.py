from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class DnfPluginPathDetected(Model):
    """
    This model contains information about whether DNF pluginpath option is configured in /etc/dnf/dnf.conf.
    """
    topic = SystemInfoTopic

    is_pluginpath_detected = fields.Boolean()
    """
    True if pluginpath option is found in /etc/dnf/dnf.conf, False otherwise.
    """
