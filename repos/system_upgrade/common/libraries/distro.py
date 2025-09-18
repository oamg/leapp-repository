import json
import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import repofileutils, rhsm
from leapp.libraries.common.config import get_distro_id
from leapp.libraries.common.config.version import get_target_major_version
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


class UnknownDistributionError(Exception):
    pass


def _get_distro_repofiles(distro, major_version, arch):
    """
    Get distribution provided repofiles.

    Note that this does not perform any validation, the caller must check
    whether the files exist.

    :param distro: The distribution to get repofiles for.
    :type distro: str
    :param major_version: The major version to get repofiles for.
    :type major_version: str
    :param arch: The architecture to get repofiles for.
    :type arch: str
    :return: A list of paths to repofiles provided by distribution
    :rtype: list[str]
    :raise UnknownDistributionError: If the distro provided repofiles are not known
    """

    # distro -> major_version -> repofile -> <architecture spec>
    # <architecture spec> - either the string 'all' if present on all or
    #                       a list of specific archs the repofile is present on
    distro_repofiles_map = {
        "rhel": {
            "8": {"/etc/yum.repos.d/redhat.repo": "all"},
            "9": {"/etc/yum.repos.d/redhat.repo": "all"},
            "10": {"/etc/yum.repos.d/redhat.repo": "all"},
        },
        "centos": {
            "8": {
                # TODO is this true on all archs?
                "CentOS-Linux-AppStream.repo": "all",
                "CentOS-Linux-BaseOS.repo": "all",
                "CentOS-Linux-ContinuousRelease.repo": "all",
                "CentOS-Linux-Debuginfo.repo": "all",
                "CentOS-Linux-Devel.repo": "all",
                "CentOS-Linux-Extras.repo": "all",
                "CentOS-Linux-FastTrack.repo": "all",
                "CentOS-Linux-HighAvailability.repo": "all",
                "CentOS-Linux-Media.repo": "all",
                "CentOS-Linux-Plus.repo": "all",
                "CentOS-Linux-PowerTools.repo": "all",
                "CentOS-Linux-Sources.repo": "all",
            },
            "9": {
                "/etc/yum.repos.d/centos.repo": "all",
                "/etc/yum.repos.d/centos-addons.repo": "all",
            },
            "10": {
                "/etc/yum.repos.d/centos.repo": "all",
                "/etc/yum.repos.d/centos-addons.repo": "all",
            },
        },
        "almalinux": {
            "8": {
                # TODO is this true on all archs?
                '/etc/yum.repos.d/almalinux-ha.repo': 'all',
                '/etc/yum.repos.d/almalinux-nfv.repo': 'all',
                '/etc/yum.repos.d/almalinux-plus.repo': 'all',
                '/etc/yum.repos.d/almalinux-powertools.repo': 'all',
                '/etc/yum.repos.d/almalinux-resilientstorage.repo': 'all',
                '/etc/yum.repos.d/almalinux-rt.repo': 'all',
                '/etc/yum.repos.d/almalinux-sap.repo': 'all',
                '/etc/yum.repos.d/almalinux-saphana.repo': 'all',
                '/etc/yum.repos.d/almalinux.repo': 'all',
            },
            "9": {
                "/etc/yum.repos.d/almalinux-appstream.repo": "all",
                "/etc/yum.repos.d/almalinux-baseos.repo": "all",
                "/etc/yum.repos.d/almalinux-crb.repo": "all",
                "/etc/yum.repos.d/almalinux-extras.repo": "all",
                "/etc/yum.repos.d/almalinux-highavailability.repo": "all",
                "/etc/yum.repos.d/almalinux-plus.repo": "all",
                "/etc/yum.repos.d/almalinux-resilientstorage.repo": "all",
                "/etc/yum.repos.d/almalinux-sap.repo": "all",
                "/etc/yum.repos.d/almalinux-saphana.repo": "all",
                # RT and NFV are only on x86_64 on almalinux 9
                "/etc/yum.repos.d/almalinux-nfv.repo": ["x86_64"],
                "/etc/yum.repos.d/almalinux-rt.repo": ["x86_64"],
            },
            "10": {
                # no resilientstorage on 10
                "/etc/yum.repos.d/almalinux-appstream.repo": "all",
                "/etc/yum.repos.d/almalinux-baseos.repo": "all",
                "/etc/yum.repos.d/almalinux-crb.repo": "all",
                "/etc/yum.repos.d/almalinux-extras.repo": "all",
                "/etc/yum.repos.d/almalinux-highavailability.repo": "all",
                "/etc/yum.repos.d/almalinux-plus.repo": "all",
                "/etc/yum.repos.d/almalinux-sap.repo": "all",
                "/etc/yum.repos.d/almalinux-saphana.repo": "all",
                # RT and NFV are only on x86_64 on almalinux 10
                "/etc/yum.repos.d/almalinux-nfv.repo": ["x86_64"],
                "/etc/yum.repos.d/almalinux-rt.repo": ["x86_64"],
            },
        },
    }

    repofiles = []
    distro_repofiles = distro_repofiles_map.get(distro)
    if not distro_repofiles:
        raise UnknownDistributionError

    # if it's not mapped it's probably an error
    # on our side, so let's warn and return empty
    version_repofiles = distro_repofiles.get(major_version, {})
    api.current_logger().warning(
        "No distro repofiles mapped for {} for major version {}".format(
            distro, major_version
        )
    )

    for repofile, archs in enumerate(version_repofiles):
        if archs is str and archs is all:
            repofiles.append(repofile)
        elif archs is list and arch in archs:
            repofiles.append(repofile)
        else:
            raise ValueError(
                "Unexpected value for architecture spec for repofile {}: {}".format(
                    repofile, archs
                )
            )
    return repofiles


def get_target_distro_repoids(context):
    """
    Get repoids defined in distro provided repofiles

    See the generic :func:`_get_distro_repoids` for more details.

    :param context: An instance of mounting.IsolatedActions class
    :type context: mounting.IsolatedActions
    :return: Repoids of distribution provided repositories
    :type: list[str]
    """

    return get_distro_repoids(
        context,
        get_distro_id(),
        get_target_major_version(),
        api.current_actor().configuration.architecture
    )


def get_distro_repoids(context, distro, major_version, arch):
    """
    Get repoids defined in distro provided repofiles

    On RHEL with RHSM this delegates to rhsm.get_available_repo_ids.

    Repofiles installed by RHUI client packages are not covered by this
    function.

    :param context: An instance of mounting.IsolatedActions class
    :type context: mounting.IsolatedActions
    :param distro: The distro whose repoids to return
    :type distro: str
    :param major_version: The major version to get distro repoids for.
    :type major_version: str
    :param arch: The architecture to get distro repoids for.
    :type arch: str
    :return: Repoids of distribution provided repositories
    :type: list[str]
    """

    if distro == 'rhel':
        if rhsm.skip_rhsm():
            return []
        # Kept this todo here from the original code from
        # userspacegen._get_rh_available_repoids:
        # Get the RHSM repos available in the target RHEL container
        # TODO: very similar thing should happens for all other repofiles in container
        return rhsm.get_available_repo_ids(context)

    repofiles = repofileutils.get_parsed_repofiles(context)
    distro_repofiles = _get_distro_repofiles(distro, major_version, arch)
    distro_repoids = []
    for rfile in repofiles:
        if not os.path.exists(context.full_path(rfile)):
            api.current_logger().debug(
                "Expected distribution provided repofile does not exists: {}".format(
                    rfile
                )
            )
            continue

        if rfile.file in distro_repofiles and rfile.data:
            distro_repoids.extend([repo.repoid for repo in rfile.data])

    return sorted(distro_repoids)
