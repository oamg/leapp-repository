from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class NetworkManagerConnectionProperty(Model):
    """
    Name-value pair for NetworkManager properties.

    This model is not expected to be used as a message (produced/consumed by actors).
    It is used within NetworkManagerConnectionSetting of a NetworkManagerConnection.
    """
    topic = SystemInfoTopic

    name = fields.String()
    """ Name of a property """
    value = fields.String()
    """ Value of a property """


class NetworkManagerConnectionSetting(Model):
    """
    NetworkManager setting, composed of a name and a list of name-value pairs.

    This model is not expected to be used as a message (produced/consumed by actors).
    It is used within NetworkManagerConnection.
    """
    topic = SystemInfoTopic

    name = fields.String()
    """ The NetworkManager setting name """
    properties = fields.List(fields.Model(NetworkManagerConnectionProperty), default=[])
    """ The name-value pair for every setting property """


class NetworkManagerConnection(Model):
    """
    NetworkManager native keyfile connection

    Produced for every connection profile loaded from INI-stile files
    described in nm-settings-keyfile(5) manual.
    """
    topic = SystemInfoTopic

    settings = fields.List(fields.Model(NetworkManagerConnectionSetting), default=[])
    """ List of NetworkManager settings """
    filename = fields.String()
    """ Path to file this model was populated from """
