"""
Establish content access inside the scratch container.

This is done so that ``dnf`` running inside the scratch container can see the
target repositories. The order of operations matters: the RHUI client is
swapped first (only when cloud RHUI is in use), then RHSM is switched into
container mode and to the target product certificate, then the CentOS Stream
``$stream`` dnf variable is adjusted, and finally any custom repository files
are installed.
"""

import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_rhui
from leapp.libraries.common import rhsm
from leapp.libraries.common.config import get_target_distro_id
from leapp.libraries.common.config.version import get_target_major_version, get_target_version
from leapp.libraries.stdlib import api

_YUM_REPOS_D = '/etc/yum.repos.d'
_DNF_STREAM_VAR = '/etc/dnf/vars/stream'


def _adjust_dnf_stream_variable(context_scratch, target_major, varfile=_DNF_STREAM_VAR):
    """
    Adjust the dnf ``stream`` variable to the target version.

    URLs in CentOS Stream repository files contain the ``$stream`` variable.
    If it is not adjusted it keeps the value from the source system, which makes
    the URLs point to repositories for the source version. This writes the target
    value so that the URLs point to the target version repositories.

    :param context_scratch: The scratch container in which the variable file is written.
    :type context_scratch: mounting.IsolatedActions
    :param target_major: The target system major version string.
    :type target_major: str
    :param varfile: Path to the dnf stream variable file inside the container.
    :type varfile: str
    :raises StopActorExecutionError: When the variable file cannot be written.
    """

    api.current_logger().debug('Writing the dnf $stream variable for the CentOS target.')
    new_dnf_stream_val = f'{target_major}-stream\n'
    try:
        with context_scratch.open(varfile, 'w') as f:
            f.write(new_dnf_stream_val)
    except (FileNotFoundError, OSError) as e:
        raise StopActorExecutionError(
            message='Failed to adjust dnf variable in {} to "{}".'.format(varfile, new_dnf_stream_val),
            details={'details': str(e)})


def _install_custom_repofiles(context_scratch, custom_repofiles):
    """
    Install the given custom repository files into the container.

    The repository files are copied from the host into the ``/etc/yum.repos.d``
    directory inside the container.

    :param context_scratch: The scratch container to copy the repofiles into.
    :type context_scratch: mounting.IsolatedActions
    :param custom_repofiles: The custom repository files to install.
    :type custom_repofiles: List[CustomTargetRepositoryFile]
    """
    api.current_logger().debug('Installing custom repositories into the scratch container.')
    for rfile in custom_repofiles:
        dst_path = os.path.join('/etc/yum.repos.d', os.path.basename(rfile.file))
        context_scratch.copy_to(rfile.file, dst_path)


def establish(context_scratch, inputs):
    """
    Establish content access inside the scratch container.

    Performs, in order: an RHUI client swap (only when cloud RHUI info is
    available), switching RHSM into container mode and to the target product
    certificate, adjusting the CentOS Stream ``$stream`` dnf variable for CentOS
    targets, and installing custom repository files.

    The product-certificate switch is intentionally left to propagate its
    exception so that the caller can turn it into the appropriate inhibitor.

    :param context_scratch: An entered nspawn scratch container.
    :type context_scratch: mounting.NspawnActions
    :param inputs: The :class:`~.tus_inputdata.InputData` value object.
    :type inputs: tus_inputdata.InputData
    :raises StopActorExecutionError: When the dnf ``$stream`` variable cannot be written.

    .. seealso::
        :func:`leapp.libraries.common.rhsm.switch_certificate` for the exception
        raised when the target product certificate is missing.
        :func:`leapp.libraries.actor.tus_rhui.perform_client_swap` for exceptions
        raised during the RHUI client swap.
    """
    target_major = get_target_major_version()

    # 1. RHUI (cloud) client swap - only when RHUIInfo is consumed.
    if inputs.rhui_info:
        tus_rhui.perform_client_swap(
            context_scratch,
            inputs.rhui_info,
            get_target_version(),
            inputs.skip_rhsm,
        )

    # 2. RHSM: container mode, then switch to the target product certificate.
    #    switch_certificate is @with_rhsm, so it is a no-op when RHSM is skipped.
    #    MissingTargetProductCertificate is intentionally NOT caught here.
    rhsm.set_container_mode(context_scratch)
    rhsm.switch_certificate(context_scratch, inputs.rhsm_info)

    # 3. CentOS Stream $stream variable - only for a CentOS target.
    if get_target_distro_id() == 'centos':
        _adjust_dnf_stream_variable(context_scratch, target_major)

    # 4. Install custom repofiles into the container.
    _install_custom_repofiles(context_scratch, inputs.custom_repofiles)
