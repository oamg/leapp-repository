from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class LDConfigFile(Model):
    """
    Represents a config file related to dynamic linker configuration
    """
    topic = SystemFactsTopic

    path = fields.String()
    """ Absolute path to the configuration file """

    modified = fields.Boolean()
    """ If True the file is considered custom and will trigger a report """


class MainLDConfigFile(LDConfigFile):
    """
    Represents the main configuration file of the dynamic linker /etc/ld.so.conf
    """
    topic = SystemFactsTopic

    modified_lines = fields.List(fields.String(), default=[])
    """ Lines that are considered custom, generally those that are not includes of other configs """


class DynamicLinkerConfiguration(Model):
    """
    Facts about configuration of dynamic linker
    """
    topic = SystemFactsTopic

    main_config = fields.Model(MainLDConfigFile)
    """ The main configuration file of dynamic linker (/etc/ld.so.conf) """

    included_configs = fields.List(fields.Model(LDConfigFile))
    """ All the configs that are included by the main configuration file """

    used_variables = fields.List(fields.String(), default=[])
    """ Environment variables that are currently used to modify dynamic linker configuration """
