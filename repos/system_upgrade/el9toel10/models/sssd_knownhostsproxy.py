from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class KnownHostsProxyConfig(Model):
    """
    SSSD and SSH configuration that is related to the sss_ssh_knownhostsproxy tool.
    """
    topic = SystemInfoTopic

    sssd_config_files = fields.List(fields.String(), default=[])
    """
    List of files in the sssd configuration that include `service`
    and that may need to be updated.
    """

    ssh_config_files = fields.List(fields.String(), default=[])
    """
    List of files in the ssh configuration that include `sss_ssh_knownhostsproxy`
    and that need to be updated.
    """
