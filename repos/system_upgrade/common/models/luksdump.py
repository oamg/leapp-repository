from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class LuksToken(Model):
    """
    Represents a single token associated with the LUKS device.

    Note this model is supposed to be used just as part of the LuksDump msg.
    """
    topic = SystemInfoTopic

    token_id = fields.Integer()
    """
    Token ID (as seen in the luksDump)
    """

    keyslot = fields.Integer()
    """
    ID of the associated keyslot
    """

    token_type = fields.String()
    """
    Type of the token. For "clevis" type the concrete subtype (determined using
    clevis luks list) is appended e.g. clevis-tpm2. clevis-tang, ...
    """


class LuksDump(Model):
    """
    Information about a single LUKS-encrypted device.

    Note this model is supposed to be used as a part of LuksDumps msg.
    """
    topic = SystemInfoTopic

    version = fields.Integer()
    """
    LUKS version
    """

    uuid = fields.String()
    """
    UUID of the LUKS device
    """

    device_path = fields.String()
    """
    Full path to the backing device
    """

    device_name = fields.String()
    """
    Device name of the backing device
    """

    tokens = fields.List(fields.Model(LuksToken), default=[])
    """
    List of LUKS2 tokens
    """


class LuksDumps(Model):
    """
    Information about all LUKS-encrypted devices on the system.
    """
    topic = SystemInfoTopic

    dumps = fields.List(fields.Model(LuksDump))
    """
    List of LuksDump representing all the encrypted devices on the system.
    """
