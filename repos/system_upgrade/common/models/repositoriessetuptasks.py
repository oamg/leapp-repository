from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class RepositoriesSetupTasks(Model):
    """
    Information about repositories that must be managed in order to complete upgrade process.

    * 'to_enable' field consists of a list of repositories that should be enabled in order to complete
    upgrade process. This information should be processed by an actor dedicated to manage
    repositories.
    * 'blocklist' field consists of a list of repositories that should be ignored during upgrade process.
    """
    topic = SystemFactsTopic

    to_enable = fields.List(fields.String(), default=[])
    """
    List of repositories that should be enabled and used during the upgrade.
    """

    blocklist = fields.List(fields.String(), default=[])
    """
    List of repositories that should be ignored during the upgrade.
    """
    # TODO(pstodulk): update the docstring to:
    # * what has precedence? to_enable or blocklist?
    # * note the effect of custom repositories!
