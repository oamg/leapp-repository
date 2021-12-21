from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class FirewalldUsedObjectNames(Model):
    """
    This model contains lists of firewalld object (e.g. zones, services) names
    in use by the permanent firewalld configuration.
    """
    topic = SystemInfoTopic

    services = fields.List(fields.String(), default=[])
    """
    list of services (names) in use by firewalld's permanent configuration

    e.g. ["ssh", "https"]
    """

    policies = fields.List(fields.String(), default=[])
    """
    list of policies (names) in use by firewalld's permanent configuration

    e.g. ["allow-host-ipv6", "mypolicy"]
    """

    zones = fields.List(fields.String(), default=[])
    """
    list of zones (names) in use by firewalld's permanent configuration

    e.g. ["public", "internal", "nm-shared", "libvirt"]
    """
