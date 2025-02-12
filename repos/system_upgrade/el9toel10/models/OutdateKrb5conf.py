from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class RpmKrb5conf(Model):
    topic = SystemInfoTopic

    path = fields.String()
    rpm = fields.String()


class OutdatedKrb5conf(Model):
    """
    Provides a list of outdated krb5 conf files.
    """
    topic = SystemInfoTopic

    unmanaged_files = fields.List(fields.String(), default=[])
    rpm_provided_files = fields.List(fields.Model(RpmKrb5conf), default=[])
    """
    The list with the full path to the krb5 conf files.
    """
