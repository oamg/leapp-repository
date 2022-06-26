from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class PkgManagerInfo(Model):
    """
    Package manager (yum/dnf) related info

    We expect to have only one single message of this kind produced
    """
    topic = SystemInfoTopic

    etc_releasever = fields.Nullable(fields.String())
    """
    Contain the first line of /etc/{yum,dnf}/vars/releasever file or None if the file does not exist.

    In case the value is empty string, it means the file exists but it is empty. In such a case the
    original configuration is obviously broken.
    """

    configured_proxies = fields.List(fields.String(), default=[])
    """
    A sorted list of proxies present in yum and dnf configuration files.
    """

    enabled_plugins = fields.List(fields.String(), default=[])
