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

import os
import shutil

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_constants, tus_repoaccess, tus_rhui
from leapp.libraries.common import mounting, rhsm, utils
from leapp.libraries.common.dnflibs import dnfplugin
from leapp.libraries.common.config import get_env, get_source_distro_id, get_target_distro_id
from leapp.libraries.common.config.version import get_target_version
from leapp.libraries.common.gpg import get_path_to_gpg_certs
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import TargetUserSpaceInfo

_DEDICATED_LEAPP_PARTITION_URL = 'https://access.redhat.com/solutions/5057391'
# FIXME: drop the constant
_PERSISTENT_PACKAGE_CACHE_ENV = 'LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE'


def _persistent_cache_enabled():
    return get_env(_PERSISTENT_PACKAGE_CACHE_ENV, '0') == '1'


def _persistent_cache_pull(persistent_cache_path, installroot):
    """
    Restore a previously stored dnf package cache into the installroot (§12, dev only).

    No-op unless ``LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE=1``. Must be called
    after the installroot has been (re)created and before ``dnf install``. The
    persistent store lives on the real host; the installroot lives inside the
    build overlay, so the copy goes host → container.
    """
    if _persistent_cache_enabled():
        if not os.path.isdir(persistent_cache_path):
            return

        dst = os.path.join(installroot, 'var', 'cache', 'dnf')
        if os.path.exists(dst):
            run(['rm', '-rf', dst])
        shutil.move(persistent_cache_path, dst)
    # We always want to remove the persistent cache here to unclutter the system
    run(['rm', '-rf', persistent_cache_path])


def _persistent_cache_push(persistent_cache_path, installroot):
    """
    Store the installroot dnf package cache in the persistent store (§12, dev only).

    No-op unless ``LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE=1``. Must be called
    after a successful build so the cache can be reused on the next run. The copy
    goes container → host.
    """
    if not _persistent_cache_enabled():
        return
    # cleanup, just in case
    run(['rm', '-rf', persistent_cache_path])

    src = os.path.join(installroot, 'var', 'cache', 'dnf')
    if os.path.exists(src):
        shutil.move(src, persistent_cache_path)


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


def _copy_files_to_userspace(context, files):
    """
    Copy the files/dirs from the host to the `context` userspace

    :param context: the target userspace context
    :type context: mounting.IsolatedActions
    :param files: list of files that should be copied from the host to the context
    :type files: List[CopyFile]
    """
    for file_task in files:
        if not file_task.dst:
            file_task.dst = file_task.src
        if os.path.isdir(file_task.src):
            context.remove_tree(file_task.dst)
            context.copytree_to(file_task.src, file_task.dst)
        else:
            context.copy_to(file_task.src, file_task.dst)


def _create_target_userspace_dir(dst_path):
    api.current_logger().debug('Creating target userspace directories.')
    try:
        utils.makedirs(dst_path)
        api.current_logger().debug('Done creating target userspace directories.')
    except OSError:
        api.current_logger().error(
            'Failed to create temporary target userspace directories %s', dst_path, exc_info=True
        )
        # This is an attempt for giving the user a chance to resolve it on their own
        raise StopActorExecutionError(
            message='Failed to prepare environment for package download while creating directories.',
            details={
                'hint': f'Please ensure that {dst_path} is empty and modifiable.'
            }
        )


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

    # Store the cache from previous run before deleting the userspace.
    # This could be done in the previous run after installing the userspace,
    # however doing it allows reusing the cache from the previous run even if
    # persistent pkg cache was disabled for it.
    _persistent_cache_push(layout.persistent_pkg_cache_path, layout.userspace_path)

    run(['rm', '-rf', layout.userspace_path])
    _create_target_userspace_dir(layout.userspace_path)

    _persistent_cache_pull(layout.persistent_pkg_cache_path, layout.userspace_path)

    installroot = context.full_path(layout.installroot_overlay_mountpoint)
    with mounting.BindMount(source=layout.userspace_path, target=installroot):
        if not inputs.nogpgcheck:
            try:
                _import_gpg_keys(context, layout.installroot_overlay_mountpoint)
            except CalledProcessError as e:
                raise StopActorExecutionError(
                    message=(
                        'Unable to import GPG certificates to install target OS userspace packages.'
                    ),
                    details={'details': str(e), 'stderr': e.stderr}
                )

        cmd = _build_dnf_install_cmd(
            layout.installroot_overlay_mountpoint,
            layout.target_major,
            releasever,
            repoids,
            inputs.skip_rhsm,
            inputs.nogpgcheck,
            inputs.packages,
        )
        try:
            context.call(cmd)
        except CalledProcessError as e:
            _diagnose_dnf_failure(e, inputs)

    # Prepare certificate / repository-file access inside the built userspace (§11).
    tus_repoaccess.prep_repository_access(context, layout.userspace_path)

    with mounting.NspawnActions(base_dir=layout.userspace_path) as us_ctx:
        # Copy the requested files into the userspace (§9).
        _copy_files_to_userspace(us_ctx, inputs.copy_files)

        # Install the leapp DNF plugin into the userspace (§9).
        dnfplugin.install(us_ctx.base_dir)

        # Cloud: R6/R7 injected-repofile cleanup - only when not bootstrapping the
        # target client, after the plugin install and before container mode is set.
        if inputs.rhui_info and not inputs.rhui_info.target_client_setup_info.bootstrap_target_client:
            tus_rhui.cleanup_injected_repofiles(us_ctx, inputs.rhui_info)

        rhsm.set_container_mode(us_ctx)

    return TargetUserSpaceInfo(
        path=layout.userspace_path,
        scratch=layout.scratch_dir,
        mounts=layout.mounts_dir,
    )
