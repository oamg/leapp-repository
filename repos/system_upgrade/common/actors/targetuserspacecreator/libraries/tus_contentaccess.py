"""
Content-access establishment inside the scratch container (§6).

Performed so that ``dnf`` inside scratch can see the target repos. Order matters
(§4 step 3): RHUI client swap first (if any), then RHSM container-mode + product
certificate, then the CentOS Stream ``$stream`` variable, then custom repofiles.

Mid-layer module: may import ``tus_rhui``; never the reverse.
"""

import os

from leapp.libraries.actor import tus_rhui
from leapp.libraries.common import rhsm
from leapp.libraries.common.config import get_target_distro_id
from leapp.libraries.common.config.version import get_target_major_version, get_target_version
from leapp.libraries.stdlib import api

_YUM_REPOS_D = '/etc/yum.repos.d'
_DNF_STREAM_VAR = '/etc/dnf/vars/stream'


def _adjust_dnf_stream_variable(context, target_major, varfile=_DNF_STREAM_VAR):
    """
    Adjust the version in the dnf 'stream' variable to the target version.

    URLs in CentOS Stream repofiles contain the $stream variable which,
    if not adjusted, retains the value from the source system making
    the URLs point to repos for the source version. This function adjusts
    the variable so that the URLs point to the target version repos.
    """

    new_dnf_stream_val = f'{target-major}-stream\n'
    try:
        with context.open(varfile, 'w') as f:
            f.write(new_dnf_stream_val)
    except (FileNotFoundError, OSError) as e:
        raise StopActorExecutionError(
            message='Failed to adjust dnf variable in {} to "{}".'.format(varfile, new_dnf_stream_val),
            details={'details': str(e)})


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
        dst_path = os.path.join('/etc/yum.repos.d', os.path.basename(rfile.file))
        context.copy_to(rfile.file, dst_path)


def establish(context, inputs):
    """
    Establish content access inside the scratch container (§6).

    :param context: An entered nspawn scratch context.
    :param inputs: The :class:`~.tus_inputdata.InputData` value object.
    :raises rhsm.MissingTargetProductCertificate: propagated from
        ``rhsm.switch_certificate`` - translated into inhibitor #1 by the caller.
    """
    target_major = get_target_major_version()

    # 1. RHUI (cloud) client swap - only when RHUIInfo is consumed.
    if inputs.rhui_info:
        tus_rhui.perform_client_swap(
            context,
            inputs.rhui_info,
            target_major,
            get_target_version(),
            inputs.skip_rhsm,
        )

    # 2. RHSM: container mode, then switch to the target product certificate.
    #    switch_certificate is @with_rhsm, so it is a no-op when RHSM is skipped.
    #    MissingTargetProductCertificate is intentionally NOT caught here.
    rhsm.set_container_mode(context)
    rhsm.switch_certificate(context, inputs.rhsm_info)

    # 3. CentOS Stream $stream variable - only for a CentOS target.
    if get_target_distro_id() == 'centos':
        api.current_logger().debug('Writing the dnf $stream variable for the CentOS target.')
        _adjust_dnf_stream_variable(context, target_major)

    # 4. Install custom repofiles into the container.
    _install_custom_repofiles(context, inputs.custom_repofiles)
