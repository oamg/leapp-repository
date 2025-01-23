from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class IfCfgProperty(Model):
    """
    Key-value pair for ifcfg properties.

    This model is not expected to be used as a message (produced/consumed by actors).
    It is used from within the IfCfg model.
    """
    topic = SystemInfoTopic

    name = fields.String()
    """ Name of a property """
    value = fields.Nullable(fields.String())
    """ Value of a property """


class IfCfg(Model):
    """
    IfCfg file describing legacy network configuration

    Produced for every ifcfg file loaded from key-value ("sysconfig")
    format described in nm-settings-ifcfg-rh(5) manual.
    """
    topic = SystemInfoTopic

    filename = fields.String()
    """ Path to file this model was populated from """
    properties = fields.List(fields.Model(IfCfgProperty), default=[])
    """ The list of name-value pairs from ifcfg file """
    secrets = fields.Nullable(fields.List(fields.Model(IfCfgProperty)))
    """ The list of name-value pairs from keys file """
    rules = fields.Nullable(fields.List(fields.String()))
    """ The list of traffic rules for IPv4 """
    rules6 = fields.Nullable(fields.List(fields.String()))
    """ The list of traffic rules for IPv6 """
    routes = fields.Nullable(fields.List(fields.String()))
    """ The list of routes for IPv4 """
    routes6 = fields.Nullable(fields.List(fields.String()))
    """ The list of routes for IPv6 """
