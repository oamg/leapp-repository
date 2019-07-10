from leapp.models import Model, fields
from leapp.topics import SystemFactsTopic


class WhitelistedKernelModules(Model):
    """
    whitelisted_modules: list of module names that are considered whitelisted
    and are not going to inhibit the upgrade
    """
    topic = SystemFactsTopic
    whitelisted_modules = fields.List(fields.String(), default=[])
