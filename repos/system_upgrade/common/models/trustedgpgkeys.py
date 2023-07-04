from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class GpgKey(Model):
    """
    GPG Public key

    It is represented by a record in the RPM DB or by a file in directory with trusted keys (or both).
    """
    topic = SystemFactsTopic
    fingerprint = fields.String()
    rpmdb = fields.Boolean()
    filename = fields.Nullable(fields.String())


class TrustedGpgKeys(Model):
    topic = SystemFactsTopic
    items = fields.List(fields.Model(GpgKey), default=[])
