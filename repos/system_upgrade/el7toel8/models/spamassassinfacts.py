from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class SpamassassinFacts(Model):
    topic = SystemInfoTopic

    spamc_ssl_argument = fields.Nullable(fields.String())
    """
    SSL version specified by the --ssl option in the spamc config file, or None
    if no value is given.
    """

    spamd_ssl_version = fields.Nullable(fields.String())
    """
    SSL version specified by the --ssl-version in the spamassassin sysconfig file,
    or None if no value is given.
    """

    service_overriden = fields.Boolean()
    """
    True if spamassassin.service is overridden, else False.
    """
