import os

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
    repofile = repofileutils.parse_repofile(CUSTOM_REPO_PATH)
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
