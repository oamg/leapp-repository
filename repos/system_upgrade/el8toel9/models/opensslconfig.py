from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class OpenSslConfigPair(Model):
    """
    Key-value pair in the OpenSSL config block

    [ name ]
    key = value
    key2 = value2
    ...

    This model is not expected to be used as a message (produced/consumed by actors).
    See the OpenSslConfig.
    """
    topic = SystemInfoTopic

    key = fields.String()
    """ The key is usually fixed name for specific purpose """
    value = fields.String()
    """ The value, can be a reference to another block """


class OpenSslConfigBlock(Model):
    """
    Every block in the openssl.cnf in the following format:

    [ name ]
    key = value
    key2 = value2
    ...

    This model is not expected to be used as a message (produced/consumed by actors).
    See the OpenSslConfig.
    """
    topic = SystemInfoTopic

    name = fields.String()
    """ The block name """
    pairs = fields.List(fields.Model(OpenSslConfigPair))
    """ The key-value pairs """


class OpenSslConfig(Model):
    """
    openssl.cnf

    This mode contains interesting parts of the RHEL8 OpenSSL configuration file
    that will be later used to decide if it needs to be updated to keep working
    in RHEL9.
    """
    topic = SystemInfoTopic

    openssl_conf = fields.Nullable(fields.String())
    """
    The value of openssl_conf field

    It is used to load default TLS policy in RHEL8, but controls loading of all
    providers in RHEL9 so it needs to be adjusted for upgrade. This is listed
    befor any block.
    """

    blocks = fields.List(fields.Model(OpenSslConfigBlock))
    """
    The list of blocks in the openssl.cnf

    We are mostly interested in the ones referenced by the openssl_conf value above.
    """

    modified = fields.Boolean(default=False)
    """ True if the configuration file was modified. """
