from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class CupsChangedFeatures(Model):
    topic = SystemInfoTopic

    interface = fields.Boolean(default=False)
    """
    True if interface scripts are used, False otherwise
    """

    digest = fields.Boolean(default=False)
    """
    True if Digest/BasicDigest directive values are used, False otherwise
    """

    include = fields.Boolean(default=False)
    """
    True if Include directive is used, False otherwise
    """

    certkey = fields.Boolean(default=False)
    """
    True if ServerKey/ServerCertificate directives are used, False otherwise
    """

    env = fields.Boolean(default=False)
    """
    True if PassEnv/SetEnv directives are used, False otherwise
    """

    printcap = fields.Boolean(default=False)
    """
    True if PrintcapFormat directive is used, False otherwise
    """

    include_files = fields.List(fields.String(), default=['/etc/cups/cupsd.conf'])
    """
    Paths to included files, contains /etc/cups/cupsd.conf by default
    """
