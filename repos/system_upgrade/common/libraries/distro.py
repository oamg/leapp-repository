import json
import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import repofileutils, rhsm
from leapp.libraries.common.config import get_target_distro_id
from leapp.libraries.common.config.architecture import ARCH_ACCEPTED, ARCH_X86_64
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


# distro -> major_version -> repofile -> tuple of architectures where it's present
_DISTRO_REPOFILES_MAP = {
    'rhel': {
        '8': {'/etc/yum.repos.d/redhat.repo': ARCH_ACCEPTED},
        '9': {'/etc/yum.repos.d/redhat.repo': ARCH_ACCEPTED},
        '10': {'/etc/yum.repos.d/redhat.repo': ARCH_ACCEPTED},
    },
    'centos': {
        '8': {
            # TODO is this true on all archs?
            'CentOS-Linux-AppStream.repo': ARCH_ACCEPTED,
            'CentOS-Linux-BaseOS.repo': ARCH_ACCEPTED,
            'CentOS-Linux-ContinuousRelease.repo': ARCH_ACCEPTED,
            'CentOS-Linux-Debuginfo.repo': ARCH_ACCEPTED,
            'CentOS-Linux-Devel.repo': ARCH_ACCEPTED,
            'CentOS-Linux-Extras.repo': ARCH_ACCEPTED,
            'CentOS-Linux-FastTrack.repo': ARCH_ACCEPTED,
            'CentOS-Linux-HighAvailability.repo': ARCH_ACCEPTED,
            'CentOS-Linux-Media.repo': ARCH_ACCEPTED,
            'CentOS-Linux-Plus.repo': ARCH_ACCEPTED,
            'CentOS-Linux-PowerTools.repo': ARCH_ACCEPTED,
            'CentOS-Linux-Sources.repo': ARCH_ACCEPTED,
        },
        '9': {
            '/etc/yum.repos.d/centos.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/centos-addons.repo': ARCH_ACCEPTED,
        },
        '10': {
            '/etc/yum.repos.d/centos.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/centos-addons.repo': ARCH_ACCEPTED,
        },
    },
    'almalinux': {
        '8': {
            # TODO is this true on all archs?
            '/etc/yum.repos.d/almalinux-ha.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-nfv.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-plus.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-powertools.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-resilientstorage.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-rt.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-sap.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-saphana.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux.repo': ARCH_ACCEPTED,
        },
        '9': {
            '/etc/yum.repos.d/almalinux-appstream.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-baseos.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-crb.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-extras.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-highavailability.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-plus.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-resilientstorage.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-sap.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-saphana.repo': ARCH_ACCEPTED,
            # RT and NFV are only on x86_64 on almalinux 9
            '/etc/yum.repos.d/almalinux-nfv.repo': (ARCH_X86_64,),
            '/etc/yum.repos.d/almalinux-rt.repo': (ARCH_X86_64,),
        },
        '10': {
            # no resilientstorage on 10
            '/etc/yum.repos.d/almalinux-appstream.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-baseos.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-crb.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-extras.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-highavailability.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-plus.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-sap.repo': ARCH_ACCEPTED,
            '/etc/yum.repos.d/almalinux-saphana.repo': ARCH_ACCEPTED,
            # RT and NFV are only on x86_64 on almalinux 10
            '/etc/yum.repos.d/almalinux-nfv.repo': (ARCH_X86_64,),
            '/etc/yum.repos.d/almalinux-rt.repo': (ARCH_X86_64,),
        },
    },
}


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
    :rtype: list[str] or None if no repofiles are mapped for the arguments
    """

    distro_repofiles = _DISTRO_REPOFILES_MAP.get(distro)
    if not distro_repofiles:
        return None

    version_repofiles = distro_repofiles.get(major_version, {})
    if not version_repofiles:
        return None

    return [repofile for repofile, archs in version_repofiles.items() if arch in archs]


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
        get_target_distro_id(),
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
    if not distro_repofiles:
        # TODO: a different way of signaling an error would be preferred (e.g. returning None),
        # but since rhsm.get_available_repo_ids also raises StopActorExecutionError,
        # let's make it easier for the caller for now and use it too
        raise StopActorExecutionError(
            "No known distro provided repofiles mapped",
            details={
                "details": "distro: {}, major version: {}, architecture: {}".format(
                    distro, major_version, arch
                )
            },
        )

    distro_repoids = []
    for rfile in repofiles:
        if rfile.file in distro_repofiles:

            if not os.path.exists(context.full_path(rfile.file)):
                api.current_logger().debug(
                    "Expected distribution provided repofile does not exists: {}".format(
                        rfile
                    )
                )
                continue

            if rfile.data:
                distro_repoids.extend([repo.repoid for repo in rfile.data])

    return sorted(distro_repoids)


def distro_id_to_pretty_name(distro_id):
    """
    Get pretty name for the given distro id.

    The pretty name is what is found in the NAME field of /etc/os-release.
    """
    return {
        "rhel": "Red Hat Enterprise Linux",
        "centos": "CentOS Stream",
        "almalinux": "AlmaLinux",
    }[distro_id]
