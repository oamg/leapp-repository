from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class SSSDConfig(Model):
    """
    SSSD configuration that is related to the upgrade process.

    The configuration might belong to some other service, such as SSH,
    but because it is related to SSSD we report it.
    """
    topic = SystemInfoTopic

    sssd_config_files = fields.List(fields.String(), default = [])
    """
    List of files in the sssd configuration that include `service`
    and that may need to be updated.
    """

    ssh_config_files = fields.List(fields.String(), default = [])
    """
    List of files in the ssh configuration that include `sss_ssh_knownhostsproxy`
    and that need to be updated.
    """
