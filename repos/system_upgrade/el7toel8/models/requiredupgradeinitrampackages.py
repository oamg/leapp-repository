from leapp.models import Model, fields
from leapp.topics import BootPrepTopic


class RequiredUpgradeInitramPackages(Model):
    """ Requests packages to be installed that the leapp upgrade dracut image generation will succeed """
    topic = BootPrepTopic
    packages = fields.List(fields.String(), default=[])
    """
    List of packages names to install on the target userspace so their content can be included in the initram disk
    """
