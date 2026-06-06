from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class RepositoriesSetupTasks(Model):
    """
    Information about repositories that must be managed in order to complete upgrade process.

    * 'to_enable' field consists of a list of repositories that should be enabled in order to complete
    upgrade process. This information should be processed by an actor dedicated to manage
    repositories.
    * 'to_block' field consists of a list of repositories that should be ignored during upgrade process.

    The priority order of the requests is following:
        to_enable < to_block < "external custom enablement request"
    The external custom request can be made by user:

        * execute leapp with --enablerepo option
        * using configuration files
    """
    topic = SystemFactsTopic

    to_enable = fields.List(fields.String(), default=[])
    """
    List of repositories that should be enabled and used during the upgrade.
    """

    to_block = fields.List(fields.String(), default=[])
    """
    List of repositories that should be ignored (blocked) during the upgrade.
    """
    # TODO(pstodulk): update the docstring:
    # * what has precedence? to_enable or to_block?
    # * note the effect of custom repositories!
    # The code needs to be updated to correctly answer these Q at this moment.
