from leapp.models.fields import List
from leapp.models.configs import Config


### Nested containers?
### Duplication of default value in type_ and Config.  If we eliminate that, we need to extract default from the type_ for the documentation.
### We probably want to allow dicts in Config.  But IIRC, dicts were specifically excluded for model fields.  Do we need something that restricts where fields are valid?
### Another thing we might want is must_be_string (no conversion).  This can be helpful for things like file modes where 644 as a number would be wrong but "644" and "0644" can be inerpretted correctly
class Transaction_ToInstall(Config):
    section = "transaction"
    name = "to_install"
    type_ = fields.List(fields.String(), default=[])
    default = []
    description = """
        List of packages to be added to the upgrade transaction.
        Signed packages which are already installed will be skipped.
    """


class Transaction_ToKeep(Config):
    section = "transaction"
    name = "to_keep"
    type_ = fields.List(fields.String(), default=[
        "leapp",
        "python2-leapp",
        "python3-leapp",
        "leapp-repository",
        "snactor",
    ])
    description = """
        List of packages to be kept in the upgrade transaction.
    """


class Transaction_ToRemove(Config):
    section = "transaction"
    name = "to_remove"
    type_ = fields.List(fields.String(), default=[
        "initial-setup",
    ])
    description = """
        List of packages to be removed from the upgrade transaction.
        initial-setup should be removed to avoid it asking for EULA acceptance during upgrade.
    """
