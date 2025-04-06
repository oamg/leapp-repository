"""
Configuration keys for dnf transactions.
"""

from leapp.actors.config import Config
from leapp.models import fields

TRANSACTION_CFG_SECTION_NAME = "transaction"


# * Nested containers?
# * Duplication of default value in type_ and Config.  If we eliminate that, we need to extract
# default from the type_ for the documentation.
# * We probably want to allow dicts in Config.  But IIRC, dicts were
# specifically excluded for model fields.  Do we need something that restricts
# where fields are valid?
# * Test that type validation is strict.  For instance, giving an integer like 644 to
# a field.String() is an error.
class Transaction_ToInstall(Config):
    section = TRANSACTION_CFG_SECTION_NAME
    name = "to_install"
    type_ = fields.List(fields.String(), default=[])
    default = []
    description = """
        List of packages to be added to the upgrade transaction.
        Signed packages which are already installed will be skipped.
    """


class Transaction_ToKeep(Config):
    section = TRANSACTION_CFG_SECTION_NAME
    name = "to_keep"
    type_ = fields.List(fields.String(), default=[
        "leapp",
        "python2-leapp",
        "python3-leapp",
        "leapp-repository",
        "snactor",
    ])
    default = [
        "leapp",
        "python2-leapp",
        "python3-leapp",
        "leapp-repository",
        "snactor",
    ]
    description = """
        List of packages to be kept in the upgrade transaction. The default is
        leapp, python2-leapp, python3-leapp, leapp-repository, snactor. If you
        override this, remember to include the default values if applicable.
    """


class Transaction_ToRemove(Config):
    section = TRANSACTION_CFG_SECTION_NAME
    name = "to_remove"
    type_ = fields.List(fields.String(), default=[
        "initial-setup",
    ])
    default = ["initial-setup"]
    description = """
        List of packages to be removed from the upgrade transaction. The default
        is initial-setup which should be removed to avoid it asking for EULA
        acceptance during upgrade. If you override this, remember to include the
        default values if applicable.
    """
