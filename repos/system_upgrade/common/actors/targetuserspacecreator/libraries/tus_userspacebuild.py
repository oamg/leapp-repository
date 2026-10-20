"""
Target userspace build: run ``dnf install`` into the installroot, set up
certificate and repository-file access, copy requested files in, install the
leapp dnf plugin, clean up cloud repofiles, and translate dnf failures into
actionable errors.

High-layer module: imports ``tus_constants``, ``tus_repoaccess`` and ``tus_rhui``.

The userspace is built inside a bind-mounted overlay and ends up in its own
directory (``layout.userspace_path``); this mechanism lives in :func:`build`.
"""

import os
import re
import shutil

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_constants, tus_repoaccess, tus_rhui
from leapp.libraries.common import mounting, rhsm, utils
from leapp.libraries.common.config import get_env, get_source_distro_id, get_target_distro_id
from leapp.libraries.common.config.version import (
    get_target_major_version,
    get_target_version,
    matches_source_version,
    matches_target_version
)
from leapp.libraries.common.dnflibs import dnfplugin
from leapp.libraries.common.gpg import get_path_to_gpg_certs, iter_gpg_keyfiles
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import DNFWorkaround, InstalledRPM, TargetUserSpaceInfo

_DEDICATED_LEAPP_PARTITION_URL = 'https://access.redhat.com/solutions/5057391'


def _persistent_cache_enabled():
    return get_env('LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE', '0') == '1'


def _persistent_cache_pull(persistent_cache_path, installroot):
    """
    Restore a previously stored dnf package cache into the installroot (development only).

    The cache restore happens only when ``LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE=1``;
    the persistent store directory is removed regardless afterwards to keep the
    system uncluttered. Must be called after the installroot has been (re)created
    and before ``dnf install``. The persistent store lives on the real host; the
    installroot lives inside the build overlay, so the copy goes from host to
    container.

    :param persistent_cache_path: Path to the persistent dnf cache store on the host.
    :type persistent_cache_path: str
    :param installroot: Path to the installroot whose dnf cache is restored.
    :type installroot: str
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
    Store the installroot dnf package cache in the persistent store (development only).

    No-op unless ``LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE=1``. Should be called
    after a successful build so the cache can be reused on the next run. Any
    existing persistent store is removed first, then the installroot cache is
    moved out to it (from container to host).

    :param persistent_cache_path: Path to the persistent dnf cache store on the host.
    :type persistent_cache_path: str
    :param installroot: Path to the installroot whose dnf cache is stored.
    :type installroot: str
    """
    if not _persistent_cache_enabled():
        return
    # cleanup, just in case
    run(['rm', '-rf', persistent_cache_path])

    src = os.path.join(installroot, 'var', 'cache', 'dnf')
    if os.path.exists(src):
        shutil.move(src, persistent_cache_path)


def _import_gpg_keys_to_scratch(context_scratch, installroot):
    """
    Import the trusted target GPG keys into the installroot rpm database.

    Iterates over every file in the target GPG certificates directory and imports
    it via ``rpm --import``. If the certificates directory does not exist, logs a
    warning and returns without importing anything.

    If source has 'pqrpm' installed and target is >= 10.1 attempt to import all
    (not just PQC) keys using /usr/bin/pqrpm/rpmkeys. Otherwise PQC keys are
    not imported.

    :param context_scratch: The scratch container context used to run commands.
    :type context_scratch: mounting.IsolatedActions
    :param installroot: Path (relative to the context) of the installroot rpm database.
    :type installroot: str
    :raises CalledProcessError: If an ``rpm --import`` invocation fails.
    """

    # Import also any other keys provided by the customer in the same directory
    for certpath in iter_gpg_keyfiles(include_pqc=False):
        cmd = [
            "rpm",
            "--root", installroot,
            "--import", certpath,
        ]
        context_scratch.call(cmd, callback_raw=utils.logging_handler)

    # On RHEL 9 the system rpm stack doesn't understand PQC (gpg v6) keys,
    # there is a separate stack in /usr/lib/pqrpm that does. The pqc keys
    # need to be imported using /usr/lib/pqrpm/bin/rpmkeys.
    # This should only be done if both source and target support PQC.
    # Note: On >= 9.7, PQC is supported for signing and verifying packages via
    # 'pqrpm' and 'dnf-multisig-plugin', however the tool for working with PQC
    # keys, 'sq', is only available on >= 9.9 so that's what we require here.
    # Also note that this imports to the pqrpmdb -
    # /usr/lib/pqrpm/lib/sysimage/rpm/ inside the source overlay, not to the
    # "main" rpmdb.
    source_has_pqc = has_package(InstalledRPM, 'pqrpm') and matches_source_version('>= 9.9')
    target_has_pqc = matches_target_version('>= 10.1')
    if not source_has_pqc or not target_has_pqc:
        return

    api.current_logger().debug('Trying to import keys to pqrpmdb')
    for certpath in iter_gpg_keyfiles(include_pqc=True):
        cmd = [
            "/usr/lib/pqrpm/bin/rpmkeys",
            "--root", installroot,
            "--import", certpath,
        ]
        context_scratch.call(cmd, callback_raw=utils.logging_handler)


def _import_gpg_keys_to_target_userspace(context_tus, certs_dir):
    """
    Import RPM GPG keys from a directory in the context using rpm from the context
    """
    container_certs_dir = os.path.join(context_tus.base_dir, os.path.relpath(certs_dir, '/'))
    for certpath in iter_gpg_keyfiles(container_certs_dir, include_pqc=True):
        cmd = [
            "rpm",
            "--import", os.path.relpath(certpath, context_tus.base_dir),
        ]
        context_tus.call(cmd, callback_raw=utils.logging_handler)


def _build_dnf_install_cmd(installroot, releasever, repoids, skip_rhsm, nogpgcheck, packages):
    """
    Assemble the ``dnf install`` command used to build the target userspace.

    Builds a ``dnf install -y`` command that disables all repositories and then
    enables only the given repoids, optionally skipping GPG checks, and appends
    the requested packages.

    :param installroot: Path to the installroot to install into.
    :type installroot: str
    :param releasever: Target release version passed to dnf.
    :type releasever: str
    :param repoids: Repository IDs to enable for the install.
    :type repoids: List[str]
    :param skip_rhsm: Whether to skip RHSM-related dnf flags.
    :type skip_rhsm: bool
    :param nogpgcheck: Whether to add ``--nogpgcheck`` to the command.
    :type nogpgcheck: bool
    :param packages: Packages to install.
    :type packages: List[str]
    :returns: The assembled dnf command as a list of arguments.
    :rtype: List
    """
    cmd = ['dnf', 'install', '-y']
    if nogpgcheck:
        cmd.append('--nogpgcheck')
    cmd += tus_constants.common_dnf_flags(releasever, skip_rhsm)
    cmd += ['--installroot', installroot, '--disablerepo', '*']
    for repoid in repoids:
        cmd += ['--enablerepo', repoid]
    cmd += list(packages)
    return cmd


def _raise_insufficient_space_error(err):
    """
    Raise a hard stop describing how much more disk space ``/var/lib/leapp`` needs.

    Parses the required size out of the dnf "more space needed" stderr summary and
    raises a :class:`StopActorExecutionError` whose hint tells the user how much
    free space to add on the filesystem hosting ``/var/lib/leapp``. The original
    "Disk Requirements" section is intentionally omitted to avoid confusing users
    with a message about missing space on ``/``.

    :param err: The dnf ``CalledProcessError`` whose stderr reports the missing space.
    :type err: CalledProcessError
    :raises StopActorExecutionError: Always, with the computed free-space hint.
    """
    NO_SPACE_STR = 'more space needed on the'

    # Disk Requirements:
    #   At least <size> more space needed on the <path> filesystem.

    missing_space = [line.strip() for line in err.stderr.split('\n') if NO_SPACE_STR in line]
    size_str = re.match(r'At least (.*) more space needed', missing_space[0]).group(1)
    message = 'There is not enough space on the file system hosting /var/lib/leapp.'
    hint = (
        'Increase the free space on the filesystem hosting'
        ' /var/lib/leapp by {} at minimum. It is suggested to provide'
        ' reasonably more space to be able to perform all planned actions'
        ' (e.g. when 200MB is missing, add 1700MB or more).\n\n'
        'It is also a good practice to create dedicated partition'
        ' for /var/lib/leapp when more space is needed, which can be'
        ' dropped after the system upgrade is fully completed'
        ' For more info, see: {}'
        .format(size_str, _DEDICATED_LEAPP_PARTITION_URL)
    )
    # we do not want to confuse customers by the orig msg speaking about
    # missing space on '/'. Skip the Disk Requirements section.
    # The information is part of the hint.
    details = {'hint': hint}
    raise StopActorExecutionError(message=message, details=details)


def _diagnose_dnf_failure(error, inputs):
    """
    Translate a dnf ``CalledProcessError`` into a user-friendly hard stop. Always raises.

    Inspects the failure and attaches the most relevant hint before raising:
    insufficient disk space, a proxy configured in the dnf configuration, a proxy
    configured on an enabled repository, or (for CentOS Stream to RHEL upgrades) a
    target RHEL version that may not have been released yet. When no specific cause
    is recognised the error is still raised with the raw dnf output.

    :param error: The dnf ``CalledProcessError`` to diagnose.
    :type error: CalledProcessError
    :param inputs: Input data providing ``pkg_manager_info`` and ``repositories_facts``.
    :type inputs: tus_inputdata.InputData
    :raises StopActorExecutionError: Always; the message and hints depend on the detected cause.
    """
    hint = None

    if 'more space needed on the' in error.stderr:
        # The stderr contains this error summary:
        # Disk Requirements:
        #   At least <size> more space needed on the <path> filesystem.
        _raise_insufficient_space_error(error)

    # If a proxy was set in dnf config, it should be the reason why dnf
    # failed since leapp does not support updates behind proxy yet.
    pkg_manager_info = inputs.pkg_manager_info
    if pkg_manager_info and pkg_manager_info.configured_proxies:
        hint = (
            'DNF failed to install userspace packages, likely due to the proxy '
            'configuration detected in the YUM/DNF configuration file. '
            'Make sure the proxy is properly configured in /etc/dnf/dnf.conf. '
            'It\'s also possible the proxy settings in the DNF configuration file are '
            'incompatible with the target system. A compatible configuration can be '
            'placed in /etc/leapp/files/dnf.conf which, if present, will be used during '
            'the upgrade instead of /etc/dnf/dnf.conf. '
            'In such case the configuration will also be applied to the target system.'
        )

    # Similarly if a proxy was set specifically for one of the repositories.
    # repositories_facts is a single RepositoriesFacts message (or None).
    repositories_facts = inputs.repositories_facts
    repo_files = repositories_facts.repositories if repositories_facts else []
    for repo_file in repo_files:
        if any(repo_data.proxy and repo_data.enabled for repo_data in repo_file.data):
            hint = (
                'DNF failed to install userspace packages, likely due to the proxy '
                'configuration detected in a repository configuration file.'
            )

    if get_source_distro_id() == 'centos' and get_target_distro_id() == 'rhel':
        check_rhel_release_hint = (
            'When upgrading and converting from Centos Stream to Red Hat Enterprise Linux'
            ' (RHEL), the automatically determined latest target version of RHEL'
            f" '{get_target_version()}' might not yet have been released. If so, specify"
            ' the latest released RHEL version manually using the --target-version '
            ' commandline option.'
        )

        if hint:
            # keep the proxy hint, we don't know which one is the problem
            hint = f"{hint}\n\n{check_rhel_release_hint}"
        else:
            hint = check_rhel_release_hint

    target_distro = get_target_distro_id()
    target_major = get_target_major_version()
    details = {
        'details': str(error),
        'stderr': error.stderr,
    }
    if hint is not None:
        details['hint'] = hint
    raise StopActorExecutionError(
        message=f'Unable to install target {target_distro} {target_major} userspace packages.',
        details=details
    )


def _copy_files_to_userspace(context_tus, files):
    """
    Copy the requested files and directories from the host into the userspace.

    Each copy task's ``dst`` is expected to be already populated (by
    ``tus_inputdata._normalize_copy_files``); this function does not fill it in.
    Directories are removed at the destination first and then copied recursively,
    while regular files are copied directly.

    :param context_tus: The target userspace context.
    :type context_tus: mounting.IsolatedActions
    :param files: Files/directories to copy from the host into the context.
    :type files: List[CopyFile]
    """
    for file_task in files:
        # dst is guaranteed populated by tus_inputdata._normalize_copy_files.
        if os.path.isdir(file_task.src):
            context_tus.remove_tree(file_task.dst)
            context_tus.copytree_to(file_task.src, file_task.dst)
        else:
            context_tus.copy_to(file_task.src, file_task.dst)


def _create_target_userspace_dir(dst_path):
    """
    Create the target userspace directory tree.

    :param dst_path: Directory path to create.
    :type dst_path: str
    :raises StopActorExecutionError: If the directories cannot be created, with a
        hint asking the user to ensure the path is empty and modifiable.
    """
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


def build(context_scratch, layout, inputs, used_repos):
    """
    Build the target userspace and return its :class:`TargetUserSpaceInfo`.

    Pushes and restores the development package cache, recreates the userspace
    directory, imports GPG keys, runs ``dnf install`` into a bind-mounted overlay,
    then sets up repository access, copies requested files in, installs the leapp
    dnf plugin, optionally cleans up cloud injected repofiles, and switches the
    userspace into container mode.

    :param context_scratch: The entered nspawn scratch context.
    :type context_scratch: mounting.IsolatedActions
    :param layout: The :class:`~.tus_layout.Layout`.
    :type layout: tus_layout.Layout
    :param inputs: The :class:`~.tus_inputdata.InputData`.
    :type inputs: tus_inputdata.InputData
    :param used_repos: The :class:`UsedTargetRepositories` selection.
    :type used_repos: UsedTargetRepositories
    :returns: Information about the built target userspace.
    :rtype: TargetUserSpaceInfo
    :raises StopActorExecutionError: If the userspace directory cannot be created,
        if importing the GPG keys fails, or if the ``dnf install`` fails (translated
        into an actionable error with hints).

    .. seealso::
        :func:`tus_repoaccess.prep_repository_access` for repository-access setup exceptions.

    .. seealso::
        :func:`dnfplugin.install` for leapp dnf plugin installation exceptions.

    .. seealso::
        :func:`rhsm.set_container_mode` for exceptions raised while switching the
        userspace into container mode.
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

    installroot = context_scratch.full_path(layout.installroot_overlay_mountpoint)
    with mounting.BindMount(source=layout.userspace_path, target=installroot):
        if not inputs.nogpgcheck:
            try:
                _import_gpg_keys_to_scratch(
                    context_scratch, layout.installroot_overlay_mountpoint
                )
            except CalledProcessError as e:
                raise StopActorExecutionError(
                    message=(
                        'Unable to import GPG certificates to install target OS userspace packages.'
                    ),
                    details={'details': str(e), 'stderr': e.stderr}
                )

        cmd = _build_dnf_install_cmd(
            layout.installroot_overlay_mountpoint,
            releasever,
            repoids,
            inputs.skip_rhsm,
            inputs.nogpgcheck,
            inputs.packages,
        )
        try:
            context_scratch.call(cmd)
        except CalledProcessError as e:
            _diagnose_dnf_failure(e, inputs)

    # Before userspace installation, PQC keys are imported using pqrpm, which
    # imports to the pqrpmdb inside scratch. To make transactions ran using
    # 'rpm' from target userspace, such as installation of initramfs deps work,
    # the keys need to be imported to the rpmdb inside target userspace.

    # The 'rpm' installed in target userspace can import PQC keys on >= 10.1.
    target_has_pqc = matches_target_version('>= 10.1')
    # Only handle PQC on >= 9.9 where 'sq' is available.
    source_has_pqc = matches_source_version('>= 9.9')
    # TODO(mmatuska): can this be put into the 'with' below?
    if not inputs.nogpgcheck and source_has_pqc and target_has_pqc:
        with mounting.NspawnActions(base_dir=layout.userspace_path) as container:
            container.copytree_to(get_path_to_gpg_certs(), layout.userspace_gpg_keys_dir)
            # TODO(mmatuska): we could move the exception handling into the import
            # function, same for the import above
            try:
                _import_gpg_keys_to_target_userspace(container, layout.userspace_gpg_keys_dir)
            except CalledProcessError as exc:
                raise StopActorExecutionError(
                    message=(
                        'Unable to import PQC GPG certificates to install late stage target OS'
                        ' userspace packages.'
                    ),
                    details={'details': str(exc), 'stderr': exc.stderr}
                )

        api.produce(
            DNFWorkaround(
                display_name="import trusted gpg keys to RPM DB from target userspace",
                script_path=api.current_actor().get_common_tool_path("importrpmgpgkeysintarget"),
                script_args=[layout.userspace_gpg_keys_dir],
                execution_context='container',
            )
        )

    # Prepare certificate / repository-file access inside the built userspace.
    tus_repoaccess.prep_repository_access(context_scratch, layout.userspace_path)

    with mounting.NspawnActions(base_dir=layout.userspace_path) as context_tus:
        # Copy the requested files into the userspace.
        _copy_files_to_userspace(context_tus, inputs.copy_files)

        # Install the leapp DNF plugin into the userspace.
        dnfplugin.install(context_tus.base_dir)

        # Cloud: injected-repofile cleanup - only when not bootstrapping the
        # target client, after the plugin install and before container mode is set.
        if inputs.rhui_info and not inputs.rhui_info.target_client_setup_info.bootstrap_target_client:
            tus_rhui.cleanup_injected_repofiles(context_tus, inputs.rhui_info)

        rhsm.set_container_mode(context_tus)

    return TargetUserSpaceInfo(
        path=layout.userspace_path,
        scratch=layout.scratch_dir,
        mounts=layout.mounts_dir,
    )
