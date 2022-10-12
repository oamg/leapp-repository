import os

from leapp.libraries.actor import repoinfo
from leapp.libraries.common import rhsm, rhui


def _install_custom_repofiles(context, custom_repofiles):
    """
    Install the required custom repository files into the container.

    The repository files are copied from the host into the /etc/yum.repos.d
    directory into the container.

    :param context: the container where the repofiles should be copied
    :type context: mounting.IsolatedActions class
    :param custom_repofiles: list of custom repo files
    :type custom_repofiles: List(CustomTargetRepositoryFile)
    """
    for rfile in custom_repofiles:
        _dst_path = os.path.join('/etc/yum.repos.d', os.path.basename(rfile.file))
        context.copy_to(rfile.file, _dst_path)


def prepare_repository_collection(context, indata, prod_cert_path):
    rhsm.set_container_mode(context)
    rhsm.switch_certificate(context, indata.rhsm_info, prod_cert_path)
    if indata.rhui_info:
        rhui.copy_rhui_data(context, indata.rhui_info.provider)
    _install_custom_repofiles(context, indata.custom_repofiles)


def collect_repositories(context, cloud_repo=None):
    info = repoinfo.RepositoryInformation(context, cloud_repo)
    return info
