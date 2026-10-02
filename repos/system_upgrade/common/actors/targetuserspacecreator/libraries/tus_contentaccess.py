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


def _write_stream_variable(context, target_major):
    """Write ``{major}-stream`` into the dnf ``$stream`` var (CentOS targets only)."""
    stream_value = '{}-stream'.format(target_major)
    parent = os.path.dirname(context.full_path(_DNF_STREAM_VAR))
    if not os.path.isdir(parent):
        os.makedirs(parent)
    with context.open(_DNF_STREAM_VAR, 'w') as fobj:
        fobj.write('{}\n'.format(stream_value))


def _install_custom_repofiles(context, custom_repofiles):
    """Lay each CustomTargetRepositoryFile into the container's yum.repos.d."""
    for repofile in custom_repofiles:
        dst = os.path.join(_YUM_REPOS_D, os.path.basename(repofile.file))
        context.copy_to(repofile.file, dst)


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
        _write_stream_variable(context, target_major)

    # 4. Install custom repofiles into the container.
    _install_custom_repofiles(context, inputs.custom_repofiles)
