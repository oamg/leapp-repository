from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class RemovedPAMModules(Model):
    """
    PAM modules that were removed from RHEL8 but are in current configuration.
    """
    topic = SystemFactsTopic

    modules = fields.List(fields.String())
    """
    List of PAM modules that were detected in current configuration but
    are no longer available in RHEL8.
    """
