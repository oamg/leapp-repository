from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class GpgKey(Model):
    """
    GPG Public key

    It is represented by a record in the rpmdb (or pqrpmdb) or by a file in directory with trusted keys (or both).
    """
    topic = SystemFactsTopic

    fingerprint = fields.String()

    rpmdb = fields.Boolean()
    """ True if the key is imported in the rpmdb (or pqrpmdb), False if it only comes from a trusted keys file """

    filename = fields.Nullable(fields.String())
    """ Path to the trusted keys file the key was read from and None if rpmdb is True """


class TrustedGpgKeys(Model):
    """
    List of GPG keys considered trusted on the target system.
    """
    topic = SystemFactsTopic

    items = fields.List(fields.Model(GpgKey), default=[])
    """ The trusted GPG keys gathered from the rpmdb (or pqrpmdb) and the trusted keys directory """
