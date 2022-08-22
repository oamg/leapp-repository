from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class SSSDDomainConfig(Model):
    """
    Facts found about an SSSD domain.
    """
    topic = SystemInfoTopic

    name = fields.String()
    """
    Domain name.
    """

    options = fields.List(fields.String(), default=list())
    """
    List of options related to this domain that affects the upgrade process.
    """


class SSSDConfig(Model):
    """
    List of SSSD domains and their configuration that is related to the
    upgrade process.
    """
    topic = SystemInfoTopic

    domains = fields.List(fields.Model(SSSDDomainConfig), default=list())
    """
    SSSD Domains configuration.
    """
