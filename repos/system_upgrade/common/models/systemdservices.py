from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class SystemdServicesTasks(Model):
    topic = SystemInfoTopic

    to_enable = fields.List(fields.String(), default=[])
    """
    List of systemd services to enable on the target system

    Masked services will not be enabled. Attempting to enable a masked service
    will be evaluated by systemctl as usually. The error will be logged and the
    upgrade process will continue.
    """
    to_disable = fields.List(fields.String(), default=[])
    """
    List of systemd services to disable on the target system
    """

    # Note: possible extension in case of requirement (currently not implemented):
    # to_unmask = fields.List(fields.String(), default=[])
