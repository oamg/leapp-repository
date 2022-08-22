from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class SSSDConfig8to9(Model):
    """
    SSSD configuration that is related to the upgrade process.
    """
    topic = SystemInfoTopic

    enable_files_domain_set = fields.Boolean()
    """
    True if [sssd]/enable_files_domain is explicitly set.
    """

    explicit_files_domain = fields.Boolean()
    """
    True if a domain with id_provider=files exist.
    """

    pam_cert_auth = fields.Boolean()
    """
    True if [pam]/pam_cert_auth is set to True.
    """
