import json
import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import repofileutils, rhsm
from leapp.libraries.common.config import get_distro_id
from leapp.libraries.stdlib import api


def get_distribution_data(distribution):
    distributions_path = api.get_common_folder_path('distro')

    distribution_config = os.path.join(distributions_path, distribution, 'gpg-signatures.json')
    if os.path.exists(distribution_config):
        with open(distribution_config) as distro_config_file:
            return json.load(distro_config_file)
    else:
        raise StopActorExecutionError(
            'Cannot find distribution signature configuration.',
            details={'Problem': 'Distribution {} was not found in {}.'.format(distribution, distributions_path)})


def get_distro_repofiles(distro=None):
    """
    Get distribution provided repofiles

    Note that this does not perform any validation, the caller must check
    whether the files exist.

    :return: A list of paths to repofiles provided by distribution
    :rtype: List(String)
    """
    distro = distro or get_distro_id()
    distro_provided_repofiles = {
        "rhel": [
            "/etc/yum.repos.d/redhat.repo",
        ],
        "centos": [
            "/etc/yum.repos.d/centos.repo",
            "/etc/yum.repos.d/centos-addons.repo",
        ],
    }
    return distro_provided_repofiles[distro]


def get_distro_repoids(context, distro=None):
    """
    Get repoids defined in distro provided repofiles

    On RHEL this delegates to rhsm.get_available_repo_ids.

    :param context: An instance of mounting.IsolatedActions class
    :param distro: The distro, defaults to current
    :return: Repoids of distribution provided repositories
    :type: List(String)
    """

    distro = distro or get_distro_id()
    if distro == 'rhel':
        if rhsm.skip_rhsm():
            return []
        # I kept this todo here
        # Get the RHSM repos available in the target RHEL container
        # TODO: very similar thing should happens for all other repofiles in container
        return rhsm.get_available_repo_ids(context)

    repofiles = repofileutils.get_parsed_repofiles(context)
    distro_repoids = []
    for rfile in repofiles:
        if rfile.file in get_distro_repofiles(distro) and rfile.data:
            distro_repoids.extend([repo.repoid for repo in rfile.data])

    return sorted(distro_repoids)
