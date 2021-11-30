from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class PamService(Model):
    """
    Pam service description

    This model contains information about pam modules used by specific PAM
    service/filename
    """
    topic = SystemInfoTopic

    service = fields.String()
    modules = fields.List(fields.String())
    # Should this also list includes?


class PamConfiguration(Model):
    """
    Global PAM configuration

    This model describes separate services using PAM and what pam modules are
    used in each of them. Consumer can select just the pam services he is
    interested in or scan for specific configuration throughout all the services.
    """
    topic = SystemInfoTopic

    services = fields.List(fields.Model(PamService))
