from leapp.models import Model, fields
from leapp.topics import BootPrepTopic


class UpgradeDracutModule(Model):
    """
    This model is used to influence the leapp upgrade initram disk generation by allowing to
    include dracut modules specified by this message.
    """
    topic = BootPrepTopic

    name = fields.String()
    """ Name of the dracut module that should be added (--add option of dracut) """

    module_path = fields.Nullable(fields.String(default=None))
    """
    module_path specifies dracut modules that are to be copied
    If the path is not set, the given name will just be activated.
    """
