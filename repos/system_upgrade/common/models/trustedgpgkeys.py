from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class GpgKey(Model):
    """
    GPG Public key

    It is represented by a record in the rpmdb (or pqrpmdb) or by a file in directory with trusted keys (or both).
    """
    topic = SystemFactsTopic

    fingerprint = fields.String()
    """
    The short key ID of the fingerprint
    """

    rpmdb = fields.Boolean()
    """
    True if the key is imported in the rpmdb (or pqrpmdb), False if it only comes from a trusted keys file
    """

    filename = fields.Nullable(fields.String())
    """
    Path to the trusted keys file the key was read from and None if rpmdb is True
    """


class TrustedGpgKeys(Model):
    """
    List of GPG keys considered trusted on the target system.
    """
    topic = SystemFactsTopic

    items = fields.List(fields.Model(GpgKey), default=[])
    """
    The trusted GPG keys gathered from the rpmdb (or pqrpmdb) and the trusted keys directory
    """


class MisplacedTrustedGpgKeys(Model):
    """
    GPG keys placed in an incorrect place inside the trusted keys directory

    Note: Messages of this model are only produced and relevant on source versions 9.9 and 9.10.
    On these versions post-quantum GPG keys must be placed into a separate 'pqc' subdirectory inside
    the trusted GPG keys directory while "classic" (non post-quantum) GPG keys must be placed in the
    top level of the trusted directory.

    .. seealso::
        The `trustedgpgkeysscanner` and `trustedgpgkeydircheck` actors
    """
    topic = SystemFactsTopic

    pqc_keys = fields.List(fields.Model(GpgKey), default=[])
    """
    Post-quantum GGP keys placed in an incorrect directory - the top-level of the trusted keys directory
    """

    classic_keys = fields.List(fields.Model(GpgKey), default=[])
    """
    "Classic" GGP keys placed in an incorrect directory - the pqc subdirectory of the trusted keys directory
    """
