from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class PostfixBdbConfiguration(Model):
    """
    Presence of Postfix lookup tables that use Berkeley DB (hash/btree).

    RHEL 10 Postfix no longer supports the Berkeley DB backends. Existing
    hash: and btree: maps must be converted to lmdb: before or immediately
    after the upgrade, otherwise Postfix fails to start.
    """

    topic = SystemInfoTopic

    postfix_present = fields.Boolean(default=False)
    """True when the postfix package is installed."""

    bdb_occurrences = fields.List(fields.String(), default=[])
    """
    Human-readable findings such as
    '/etc/postfix/main.cf: alias_maps = hash:/etc/aliases'.
    """
