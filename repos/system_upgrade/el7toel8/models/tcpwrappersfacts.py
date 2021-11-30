from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class DaemonList(Model):
    """
    A split up representation of a daemon_list (see host_access(5)). Example value of the
    'value' attribute: ["ALL", "EXCEPT", "in.fingerd"]
    """
    topic = SystemInfoTopic

    value = fields.List(fields.String())


class TcpWrappersFacts(Model):
    """
    A representation of tcp_wrappers configuration. Currently it only contains a list
    of daemon lists that are present in the tcp_wrappers configuration files. From this
    you can extract information on whether there is any configuration that applies to
    a specific daemon (see leapp.libraries.common.tcpwrappersutils.config_applies_to_daemon()).
    """
    topic = SystemInfoTopic

    daemon_lists = fields.List(fields.Model(DaemonList))
