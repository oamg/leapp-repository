import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import repofileutils
from leapp.libraries.stdlib import api
from leapp.models import CustomTargetRepository, CustomTargetRepositoryFile

CUSTOM_REPO_PATH = "/etc/leapp/files/leapp_upgrade_repositories.repo"


def process():
    """
    Produce CustomTargetRepository msgs for the custom repo file if the file
    exists.

    The CustomTargetRepository msg is produced for every repository inside
    the <CUSTOM_REPO_PATH> file.
    """
    if not os.path.isfile(CUSTOM_REPO_PATH):
        api.current_logger().debug(
                "The {} file doesn't exist. Nothing to do."
                .format(CUSTOM_REPO_PATH))
        return
    api.current_logger().info("The {} file exists.".format(CUSTOM_REPO_PATH))
    try:
        repofile = repofileutils.parse_repofile(CUSTOM_REPO_PATH)
    except repofileutils.InvalidRepoDefinition as e:
        raise StopActorExecutionError(
            message="Failed to parse custom repository definition: {}".format(str(e)),
            details={
                'hint': 'Ensure the repository {} definition is correct or remove it '
                        'if the repository is not needed anymore. '
                        'This issue is typically caused by missing definition of the name field. '
                        'For more information, see: https://access.redhat.com/solutions/6969001.'
                        .format(CUSTOM_REPO_PATH)
            })
    if not repofile.data:
        return
    api.produce(CustomTargetRepositoryFile(file=CUSTOM_REPO_PATH))
    for repo in repofile.data:
        api.produce(CustomTargetRepository(
            repoid=repo.repoid,
            name=repo.name,
            baseurl=repo.baseurl,
            enabled=repo.enabled,
        ))
