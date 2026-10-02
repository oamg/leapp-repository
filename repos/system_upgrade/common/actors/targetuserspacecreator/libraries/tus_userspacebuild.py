"""
Target userspace build: dnf install into the installroot, cert/repo access, file
copies, the leapp dnf plugin, cloud repofile cleanup, and dnf-failure diagnosis
(§9, §10).

High-layer module: imports the frozen ``tus_repoaccess``, ``tus_rhui``,
``tus_layout`` and ``tus_constants``.

The "build in the source overlay, then decouple into its own directory" mechanism
(§1/§9) is isolated behind :func:`_prepared_installroot`. It is review /
integration-verified rather than deeply unit-tested.
"""

import contextlib
import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_constants, tus_layout, tus_repoaccess, tus_rhui
from leapp.libraries.common import mounting, rhsm
from leapp.libraries.common.dnflibs import dnfplugin
from leapp.libraries.common.config import get_source_distro_id, get_target_distro_id
from leapp.libraries.common.config.version import get_target_version
from leapp.libraries.common.gpg import get_path_to_gpg_certs
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import TargetUserSpaceInfo

_DEDICATED_LEAPP_PARTITION_URL = 'https://access.redhat.com/solutions/5057391'


# FIXME uses copying instead of a bind mount
@contextlib.contextmanager
def _prepared_installroot(context, layout):
    """
    Prepare the installroot inside the build overlay and decouple it on success.

    The real host userspace directory is wiped and recreated; the same path
    inside the overlay is cleaned and used as the dnf ``--installroot``. On
    successful completion the freshly-built tree is copied out of the overlay
    into the real host directory (the "decouple" step).
    """
    # Wipe the real host userspace. Do NOT recreate it here: copytree_from below
    # requires the destination not to exist (it creates it, and any missing
    # parents, itself).
    run(['rm', '-rf', layout.userspace_path])

    installroot = layout.userspace_path
    context.remove_tree(installroot)
    context.makedirs(installroot)

    yield installroot

    # Decouple: copy the built userspace out of the overlay onto the real host.
    context.copytree_from(installroot, layout.userspace_path)


def _import_gpg_keys(context, installroot):
    """Import the trusted target GPG keys into the installroot rpm database (§9)."""
    certs_dir = get_path_to_gpg_certs()
    if not os.path.isdir(certs_dir):
        api.current_logger().warning('No target GPG keys directory found at {}.'.format(certs_dir))
        return
    for name in sorted(os.listdir(certs_dir)):
        key_path = os.path.join(certs_dir, name)
        context.call(['rpm', '--root', installroot, '--import', key_path])


def _build_dnf_install_cmd(installroot, target_major, releasever, repoids, skip_rhsm, nogpgcheck, packages):
    """Assemble the ``dnf install`` command for the userspace build (§10)."""
    cmd = ['dnf', 'install', '-y']
    if nogpgcheck:
        cmd.append('--nogpgcheck')
    cmd += tus_constants.common_dnf_flags(target_major, releasever, skip_rhsm)
    cmd += ['--installroot', installroot, '--disablerepo', '*']
    for repoid in repoids:
        cmd += ['--enablerepo', repoid]
    cmd += list(packages)
    return cmd


def _dnf_output_text(error):
    """Concatenate stdout+stderr of a CalledProcessError for text scanning."""
    parts = []
    for stream in (getattr(error, 'stdout', None), getattr(error, 'stderr', None)):
        if not stream:
            continue
        if isinstance(stream, list):
            parts.append('\n'.join(stream))
        else:
            parts.append(stream)
    return '\n'.join(parts)


def _diagnose_dnf_failure(error, inputs):
    """
    Translate a dnf ``CalledProcessError`` into a friendly hard stop with the
    applicable hints (§10, hints 1-4). Always raises.
    """
    output = _dnf_output_text(error)
    hints = []

    # Hint 1 - disk space.
    if 'more space needed on the' in output:
        raise StopActorExecutionError(
            message='There is not enough space on the file system to create the'
                    ' target userspace.',
            details={
                'hint': 'Consider using a dedicated partition for /var/lib/leapp.',
                'link': _DEDICATED_LEAPP_PARTITION_URL,
                'details': output,
            }
        )

    # Hint 2 - proxy configured in dnf.conf.
    pkg_manager_info = inputs.pkg_manager_info
    if pkg_manager_info and pkg_manager_info.configured_proxies:
        hints.append('A proxy is configured in dnf.conf. Leapp is not supported'
                     ' behind a proxy configured that way.')

    # Hint 3 - proxy configured in a .repo file.
    repositories_facts = inputs.repositories_facts
    if repositories_facts:
        for repofile in repositories_facts.repositories:
            if any(repo.proxy for repo in repofile.data):
                hints.append('A proxy is configured in a .repo file. Leapp is not'
                             ' supported behind a proxy configured that way.')
                break

    # Hint 4 - CentOS -> RHEL target not released yet.
    if get_source_distro_id() == 'centos' and get_target_distro_id() == 'rhel':
        hints.append('The target RHEL version may not be released yet. Try setting'
                     ' the target version explicitly via LEAPP_DEVEL_TARGET_RELEASE'
                     ' / --target-version.')

    raise StopActorExecutionError(
        message='Failed to install the target userspace packages using dnf.',
        details={
            'hints': hints,
            'details': output,
        }
    )


def _copy_files(context, copy_files, userspace_path):
    """Copy the (de-duplicated) requested files into the built userspace."""
    for copy_file in copy_files:
        dst = copy_file.dst if copy_file.dst else copy_file.src
        full_dst = os.path.join(userspace_path, dst.lstrip('/'))
        run(['mkdir', '-p', os.path.dirname(full_dst)])
        context.copy_from(copy_file.src, full_dst)


def build(context, layout, inputs, used_repos):
    """
    Build the target userspace and return its :class:`TargetUserSpaceInfo` (§9).

    :param context: The entered nspawn scratch context.
    :param layout: The :class:`~.tus_layout.Layout`.
    :param inputs: The :class:`~.tus_inputdata.InputData`.
    :param used_repos: The :class:`UsedTargetRepositories` selection.
    :raises StopActorExecutionError: on dnf install failure (with §10 hints).
    """
    repoids = [repo.repoid for repo in used_repos.repos]
    releasever = get_target_version()

    with _prepared_installroot(context, layout) as installroot:
        tus_layout.persistent_cache_pull(context, layout, installroot)

        if not inputs.nogpgcheck:
            # FIXME the error from this is handled in a generic handler in _diagnose_dnf_failure
            _import_gpg_keys(context, installroot)

        cmd = _build_dnf_install_cmd(
            installroot, layout.target_major, releasever, repoids,
            inputs.skip_rhsm, inputs.nogpgcheck, inputs.packages,
        )
        try:
            context.call(cmd)
        except CalledProcessError as e:
            _diagnose_dnf_failure(e, inputs)

        tus_layout.persistent_cache_push(context, layout, installroot)

    # Prepare certificate / repository-file access inside the built userspace (§11).
    tus_repoaccess.prep_repository_access(context, layout.userspace_path)

    # Copy the requested files into the userspace (§9).
    _copy_files(context, inputs.copy_files, layout.userspace_path)

    # Install the leapp DNF plugin into the userspace (§9).
    dnfplugin.install(layout.userspace_path)

    # Cloud: R6/R7 injected-repofile cleanup - only when not bootstrapping the
    # target client, after the plugin install and before container mode is set.
    if inputs.rhui_info and not inputs.rhui_info.target_client_setup_info.bootstrap_target_client:
        with mounting.NspawnActions(base_dir=layout.userspace_path) as us_ctx:
            tus_rhui.cleanup_injected_repofiles(us_ctx, inputs.rhui_info)

    # (Re-)enter the userspace and set subscription-manager container mode (§9).
    with mounting.NspawnActions(base_dir=layout.userspace_path) as us_ctx:
        rhsm.set_container_mode(us_ctx)

    return TargetUserSpaceInfo(
        path=layout.userspace_path,
        scratch=layout.scratch_dir,
        mounts=layout.mounts_dir,
    )
