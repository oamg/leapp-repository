"""
RHUI (cloud) client-swap logic for the ``targetuserspacecreator`` actor.

The whole module is a no-op when no ``RHUIInfo`` is consumed (``rhui_info``
falsy): every public entry point guards on it and returns early. Otherwise it
swaps the source RHUI client rpm(s) for the target client rpm(s) inside the
scratch container (via ``dnf shell``), applies the pre/post-install file tasks,
and leaves ``/etc/yum.repos.d`` consistent. Every RHUI failure surfaces as a
hard stop (``StopActorExecutionError``) rather than a silent continue.
"""

import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_constants
from leapp.libraries.common import repofileutils, utils
from leapp.libraries.common.config.version import get_major_version
from leapp.libraries.stdlib import api, CalledProcessError

_YUM_REPOS_D = '/etc/yum.repos.d'


def _resolve_copy_target(context, copy_file):
    """
    Resolve the final destination path for a single file copy.

    ``copy_file.dst`` is relied upon to already be populated by the input-loading
    normalization (see ``tus_inputdata._normalize_copy_files``). If the
    destination resolves to an existing directory in the container, the file lands
    at ``destination/basename(source)``; otherwise the destination path is used
    unchanged.

    :param context: Container context used to resolve paths against its base dir.
    :type context: mounting.IsolatedActions
    :param copy_file: A ``CopyFile`` object carrying ``src`` and ``dst``.
    :type copy_file: CopyFile
    :returns: The resolved destination path relative to the container base dir.
    :rtype: str
    """
    if os.path.isdir(context.full_path(copy_file.dst)):
        return os.path.join(copy_file.dst, os.path.basename(copy_file.src))
    return copy_file.dst


def _sanitized_copy_files_iter(context, copy_files):
    """
    Yield sanitized ``(src, dst)`` pairs for a list of ``CopyFile`` objects.

    For each ``CopyFile`` the destination is resolved to reflect the expected
    final path:

      * ``dst`` is already populated at input load (an empty ``dst`` becomes
        ``src`` there)
      * if ``dst`` points to a directory, the resolved path becomes
        ``dst/basename(src)``

    The pairs are yielded sorted by the destination path. Note that at this
    moment there is no copy of dirs in this module, so it should not be a problem,
    but we will want to apply this on other places possibly as well, and probably
    it's better to be a little bit more defensive as we do not know what will be
    in future.

    :param context: Container context used to resolve destination paths.
    :type context: mounting.IsolatedActions
    :param copy_files: Iterable of ``CopyFile`` objects to sanitize.
    :type copy_files: List[CopyFile]
    :returns: Generator of ``(src, dst)`` tuples sorted by destination path.
    :rtype: Iterator[Tuple[str, str]]
    """
    src_dst_pairs = [(cf.src, _resolve_copy_target(context, cf)) for cf in copy_files]
    yield from sorted(src_dst_pairs, key=lambda p: p[1])


def _run_preinstall_tasks(context_scratch, preinstall_tasks):
    """
    Apply the RHUI pre-install file tasks into the scratch container.

    Removals are processed first, then host-to-container copies (parent
    directories are created as needed). Does nothing when ``preinstall_tasks``
    is falsy.

    :param context_scratch: Scratch container context the tasks are applied to.
    :type context_scratch: mounting.IsolatedActions
    :param preinstall_tasks: Tasks describing files to remove and to copy in.
    :type preinstall_tasks: TargetRHUIPreInstallTasks
    :raises StopActorExecutionError: When applying the pre-install file tasks fails.
    """
    if not preinstall_tasks:
        api.current_logger().debug('No RHUI preinstall tasks - skipping.')
        return

    api.current_logger().debug('Applying RHUI preinstall tasks.')
    try:
        for fpath in preinstall_tasks.files_to_remove:
            api.current_logger().debug(' -- Removing {} from the scratch container.'.format(fpath))
            context_scratch.remove(fpath)

        for src, dst in _sanitized_copy_files_iter(context_scratch, preinstall_tasks.files_to_copy_into_overlay):
            api.current_logger().debug(
                ' -- Copying {0} in {1} into the scratch container.'
                .format(src, dst)
            )
            context_scratch.makedirs(os.path.dirname(dst), exists_ok=True)
            context_scratch.copy_to(src, dst)
    except OSError as e:
        raise StopActorExecutionError(
            message='Failed to apply RHUI pre-install file tasks.',
            details={'details': str(e)}
        )


def _run_postinstall_tasks(context_scratch, postinstall_tasks):
    """
    Apply the RHUI post-install file tasks inside the scratch container.

    Performs in-container copies to each destination (parent directories are
    created as needed). Does nothing when ``postinstall_tasks`` is falsy. This is
    invoked only after a successful client swap.

    :param context_scratch: Scratch container context the tasks are applied to.
    :type context_scratch: mounting.IsolatedActions
    :param postinstall_tasks: Tasks describing in-container files to copy.
    :type postinstall_tasks: TargetRHUIPostInstallTasks
    :raises StopActorExecutionError: When applying the post-install file tasks fails.
    """
    if not postinstall_tasks:
        api.current_logger().debug('No RHUI postinstall tasks - skipping.')
        return

    api.current_logger().debug('Applying RHUI postinstall tasks.')
    try:
        for src, dst in _sanitized_copy_files_iter(context_scratch, postinstall_tasks.files_to_copy):
            api.current_logger().debug(
                ' -- Copying {0} to {1} (inside the scratch container).'
                .format(src, dst)
            )
            context_scratch.makedirs(os.path.dirname(dst), exists_ok=True)
            # NOTE: Note the use of CP instead of `copy_to` function is essential
            # as this action is designed to be performed inside the scratch
            # container context - so all paths are meant to be valid inside the container.
            # See the TargetRHUIPostInstallTasks model.
            context_scratch.call(['cp', src, dst])
    except (OSError, CalledProcessError) as e:
        raise StopActorExecutionError(
            message='Failed to apply RHUI post-install file tasks.',
            details={'details': str(e)}
        )


def _get_repofiles_paths(context):
    """
    Return the paths of all ``*.repo`` files in ``/etc/yum.repos.d``.

    Returns an empty set when the directory does not exist. The returned paths
    are relative to ``context.base_dir``.

    :param context: Container context whose ``/etc/yum.repos.d`` is inspected.
    :type context: mounting.IsolatedActions
    :returns: Set of ``*.repo`` file paths relative to the container base dir.
    :rtype: Set[str]
    """
    repos_dir = context.full_path(_YUM_REPOS_D)
    if not os.path.isdir(repos_dir):
        return set()

    basenames = [name for name in os.listdir(repos_dir) if name.endswith('.repo')]
    return {os.path.join(_YUM_REPOS_D, name) for name in basenames}


def _repofiles_copied_at_setup(context, files_to_copy_into_overlay):
    """
    Return the ``*.repo`` destination paths injected by the pre-install copies.

    Only destinations ending with ``.repo`` are included. The returned paths are
    relative to ``context.base_dir``.

    :param context: Container context used to resolve destination paths.
    :type context: mounting.IsolatedActions
    :param files_to_copy_into_overlay: Pre-install copy tasks to inspect.
    :type files_to_copy_into_overlay: List[CopyFile]
    :returns: Set of injected ``*.repo`` destination paths.
    :rtype: Set[str]
    """
    setup_copied = set()
    for dummy_src, dst in _sanitized_copy_files_iter(context, files_to_copy_into_overlay):
        if dst.endswith('.repo'):
            setup_copied.add(dst)
    return setup_copied


def _dnf_repolist_repoids(context, target_version):
    """
    Run ``dnf repolist`` and return the set of repoids, excluding source/debug.

    All repositories are enabled while the ``*-source-*`` and ``*-debug-*`` repos
    are disabled, and the repoids are parsed from the ``Repo-id`` lines of the
    verbose output.

    :param context: Container context the ``dnf repolist`` command runs in.
    :type context: mounting.IsolatedActions
    :param target_version: Release version passed to ``dnf`` via ``--releasever``.
    :type target_version: str
    :returns: Set of repoids available in the context, excluding source/debug.
    :rtype: Set[str]
    :raises CalledProcessError: When the underlying ``dnf repolist`` call fails.
    """
    repoids = set()
    cmd = [
        'dnf', 'repolist',
        '--releasever', target_version,
        '-v',
        '--enablerepo', '*',
        '--disablerepo', '*-source-*',
        '--disablerepo', '*-debug-*',
    ]
    stdout = context.call(cmd, split=True)['stdout']

    def extract_repoid_from_line(line):
        return line.split(':', 1)[1].strip()

    repoid_lines = [line for line in stdout if line.startswith('Repo-id')]
    repoids.update({extract_repoid_from_line(line) for line in repoid_lines})
    return repoids


def discover_client_exposed_repoids(context, rhui_info, target_version):
    """
    Discover the repoids exposed by the RHUI clients, leaving the repo dir intact.

    Foreign repofiles (all ``*.repo`` minus the client-owned ones minus the
    setup-copied ones) are temporarily renamed with a ``.back`` suffix so they are
    not seen by ``dnf repolist``, which is then run with only the client and setup
    repos visible. Every hidden file is renamed back in a ``finally`` block, so
    ``/etc/yum.repos.d`` is left byte-identical whether the repolist succeeds or
    fails. Returns an empty set when ``rhui_info`` is falsy.

    :param context: Container context the discovery is performed in.
    :type context: mounting.IsolatedActions
    :param rhui_info: RHUI info describing the target client setup.
    :type rhui_info: RHUIInfo
    :param target_version: Release version used for the repolist query.
    :type target_version: str
    :returns: Set of repoids exposed by the target RHUI clients.
    :rtype: Set[str]
    :raises StopActorExecutionError: When ``dnf repolist`` fails, or when querying
        the client-owned repofiles fails.
    """
    if not rhui_info:
        return set()

    def with_hidden_suffix(path):
        return '{}.back'.format(path)

    setup_info = rhui_info.target_client_setup_info

    all_repofiles = _get_repofiles_paths(context)
    api.current_logger().debug(
        '(RHUI Setup) All available repofiles: {0}'.format(' '.join(all_repofiles))
    )

    target_access_repofiles = set()
    if setup_info.bootstrap_target_client:
        target_access_repofiles = _find_rhui_client_repofiles(
            context, rhui_info.target_client_pkg_names, get_major_version(target_version)
        )

    # Exclude repofiles used to setup the target rhui access as on some platforms
    # the repos provided by the client are not sufficient to install the client
    # into target userspace (GCP)
    copy_tasks = setup_info.preinstall_tasks.files_to_copy_into_overlay
    repofiles_copied_at_setup = _repofiles_copied_at_setup(context, copy_tasks)

    # Make sure the path is relative to context.base_dir in all of the sets
    keep_visible = target_access_repofiles | repofiles_copied_at_setup
    foreign = all_repofiles - keep_visible

    api.current_logger().debug(
        'The following repofiles are considered as unknown to'
        ' the target RHUI content setup and will be ignored: {0}'.format(' '.join(foreign))
    )

    # Rename non-client repofiles so they will not be recognized when running dnf repolist
    foreign = [context.full_path(path) for path in foreign]
    for repofile in foreign:
        os.rename(repofile, with_hidden_suffix(repofile))

    try:
        return _dnf_repolist_repoids(context, target_version)
    except CalledProcessError as e:
        raise StopActorExecutionError(
            message='Failed to retrieve repoids provided by target RHUI clients.',
            details={'details': str(e), 'stderr': e.stderr}
        )
    finally:
        # Revert the renaming of non-client repofiles
        for repofile in foreign:
            os.rename(with_hidden_suffix(repofile), repofile)


def _parse_repoids_from_copied_files(copy_files):
    """
    Parse repoids from the source ``.repo`` files of the pre-install copies.

    Note the function assumes:

        * sources of repofiles have the .repo suffix (no rename of filenames
          planned for copying)
        * files were copied correctly
        * multiple sources does not point to the same destination
          (so destination is not replaced several times by preinstall tasks)

    Under these conditions, it's safe to parse repofiles from their original
    paths.

    :param copy_files: Pre-install copy tasks whose ``.repo`` sources are parsed.
    :type copy_files: List[CopyFile]
    :returns: Set of repoids defined by the copied repofiles.
    :rtype: Set[str]
    :raises StopActorExecutionError: When a repofile cannot be parsed.
    """
    copied_repofiles = [cfile.src for cfile in copy_files if cfile.src.endswith('.repo')]
    copied_repoids = set()
    for repofile in copied_repofiles:
        try:
            repofile_contents = repofileutils.parse_repofile(repofile)
        except repofileutils.InvalidRepoDefinition as e:
            raise StopActorExecutionError(
                message="Failed to parse repositories for RHUI: {}".format(str(e)),
                details={
                    'hint': 'Ensure the repository definition is correct or remove it'
                            ' if the repository is not required for the upgrade.'
                            ' Each repository definition must contain the `name` option'
                            ' and the location of the repository, configured by'
                            ' baseurl, mirrorlist, or metalink options.'
                })
        copied_repoids.update(entry.repoid for entry in repofile_contents.data)
    return copied_repoids


def _swap_clients(context_scratch, rhui_info, target_version, skip_rhsm, enable_only_repoids):
    """
    Swap the RHUI clients via a ``dnf shell`` transaction inside the container.

    A ``dnf shell`` script is written that removes the source client rpm(s) (when
    present), installs the target client rpm(s) and runs the transaction. When
    ``enable_only_repoids`` is provided, all repos are disabled and only those
    repoids are enabled for the swap. The script file is always removed afterwards.

    :param context_scratch: Scratch container context the swap runs in.
    :type context_scratch: mounting.IsolatedActions
    :param rhui_info: RHUI info providing the source/target client package names.
    :type rhui_info: RHUIInfo
    :param target_version: Release version passed to the ``dnf`` command.
    :type target_version: str
    :param skip_rhsm: Whether to skip subscription-manager related dnf flags.
    :type skip_rhsm: bool
    :param enable_only_repoids: Repoids to exclusively enable during the swap.
    :type enable_only_repoids: Set[str]
    :raises StopActorExecutionError: When the ``dnf shell`` transaction fails.
    """
    script_lines = []
    if rhui_info.src_client_pkg_names:
        script_lines.append('remove {}'.format(' '.join(rhui_info.src_client_pkg_names)))
    script_lines.append('install {}'.format(' '.join(rhui_info.target_client_pkg_names)))
    script_lines.append('transaction run')
    script_lines.append('')
    # TODO(pstodulk): name & path:
    # # it would be nice to actually standardize paths on which we store such
    # # files. Keeping as it is now until it's decided.
    script_path = '/leapp-rhui-swap.dnfsh'
    with context_scratch.open(script_path, 'w') as fobj:
        fobj.write('\n'.join(script_lines))

    cmd = ['dnf', 'shell', '-y']
    cmd += tus_constants.common_dnf_flags(target_version, skip_rhsm)
    if enable_only_repoids:
        cmd.append('--disablerepo=*')
        for repoid in sorted(enable_only_repoids):
            cmd.append('--enablerepo={}'.format(repoid))
    cmd.append(script_path)

    try:
        context_scratch.call(cmd, callback_raw=utils.logging_handler)
    except CalledProcessError as e:
        # FIXME: `inside DNF shell, failed transaction can end with 0 exit code
        # see `tools/dnfshellswap` workaround. As we have already negative
        # experience around RHUI clients in case of some cloud providers, it
        # would be worthy to cover this more properly.
        # Add more details into the error msg.
        raise StopActorExecutionError(
            message='Failed to swap RHUI clients to establish content access.',
            details={'details': str(e)}
        )
    finally:
        # TODO: actually, it would be beneficial to keep the file for debugging
        # purposes. Just we need to standardize first the path in which it will
        # be stored. Otherwise we could input this data via stdin instead.
        context_scratch.remove(script_path)


def _query_rpm_for_pkg_files(context_scratch, pkgs):
    """
    Return the set of files installed by the given rpm(s) via ``rpm -ql``.

    :param context_scratch: Container context the ``rpm`` query runs in.
    :type context_scratch: mounting.IsolatedActions
    :param pkgs: Package names to query.
    :type pkgs: List[str]
    :returns: Set of file paths owned by the given packages.
    :rtype: Set[str]
    :raises CalledProcessError: When the underlying ``rpm -ql`` call fails.
    """
    cmd = ['rpm', '-ql'] + pkgs
    result = context_scratch.call(cmd, split=True)
    return set(result['stdout'])


def _find_rhui_client_repofiles(context, pkgs, target_major_version):
    """
    Return the ``*.repo`` files in ``/etc/yum.repos.d`` owned by the client rpm(s).

    Queries the files owned by the given packages and keeps only those located in
    ``/etc/yum.repos.d`` with a ``.repo`` suffix. The returned paths are relative
    to ``context.base_dir``.

    :param context: Container context the rpm query runs in.
    :type context: mounting.IsolatedActions
    :param pkgs: Target client package names to query.
    :type pkgs: List[str]
    :param target_major_version: Target RHEL major version, used in the error msg.
    :type target_major_version: str
    :returns: Set of client-owned repofile paths.
    :rtype: Set[str]
    :raises StopActorExecutionError: When querying the files owned by the client
        rpm(s) fails.
    """
    try:
        owned_files = _query_rpm_for_pkg_files(context, pkgs)
    except CalledProcessError as err:
        # unclear what might have gone wrong here, the clients should be
        # properly installed here, report a generic failure with stderr
        client_rpms = ', '.join(pkgs)
        msg = (
            f'Failed to query repofiles owned by the RHEL {target_major_version}'
            f' RHUI clients {client_rpms}'
        )
        raise StopActorExecutionError(msg, details={'details': str(err)})

    def is_repofile(path):
        dirname = os.path.dirname(path)
        basename = os.path.basename(path)
        return dirname == '/etc/yum.repos.d' and basename.endswith('.repo')

    return {path for path in owned_files if is_repofile(path)}


def _find_rhui_client_files(context_scratch, pkgs, target_major_version):
    """
    Return all files installed by the target client rpm(s).

    A failure to query the files is treated as the target clients not being
    installed during the swap step and is turned into a hard stop.

    :param context_scratch: Scratch container context the rpm query runs in.
    :type context_scratch: mounting.IsolatedActions
    :param pkgs: Target client package names to query.
    :type pkgs: List[str]
    :param target_major_version: Target RHEL major version, used in the error msg.
    :type target_major_version: str
    :returns: Set of file paths owned by the target client rpm(s).
    :rtype: Set[str]
    :raises StopActorExecutionError: When the target client files cannot be
        queried (i.e. the target clients were not installed).
    """
    try:
        return _query_rpm_for_pkg_files(context_scratch, pkgs)
    except CalledProcessError as err:
        api.current_logger().critical(
            'Failed to query files owned by target RHUI clients (clients=%s). This is caused'
            ' by failing to install the target clients during the client-swap step.'
            ' Full error: %s',
            pkgs, err
        )

        client_rpms = ', '.join(pkgs)
        raise StopActorExecutionError(
            f'Could not find the RHEL {target_major_version} RHUI clients ({client_rpms})'
            ' in the cloud provider\'s client repository.'
        )


def _remove_nonclient_injected_files(context_scratch, rhui_info, client_files):
    """
    Remove injected setup files that are neither client-owned nor supporting.

    Iterates the pre-install copies and removes each injected file whose container
    destination is not among the client-owned files and whose source is not listed
    in ``files_supporting_client_operation``.

    :param context_scratch: Scratch container context the files are removed from.
    :type context_scratch: mounting.IsolatedActions
    :param rhui_info: RHUI info providing the setup copy tasks and supporting files.
    :type rhui_info: RHUIInfo
    :param client_files: Set of files owned by the installed target client rpm(s).
    :type client_files: Set[str]
    """
    setup = rhui_info.target_client_setup_info
    supporting = set(setup.files_supporting_client_operation)

    for src, dst in _sanitized_copy_files_iter(context_scratch, setup.preinstall_tasks.files_to_copy_into_overlay):
        if dst in client_files or src in supporting:
            continue
        context_scratch.remove(dst)


def perform_client_swap(context_scratch, rhui_info, target_version, skip_rhsm):
    """
    Orchestrate the whole RHUI client swap inside the scratch container.

    No-op when ``rhui_info`` is falsy. The steps are: apply pre-install tasks;
    return early if ``bootstrap_target_client`` is false; optionally compute the
    repoids to exclusively enable (when ``enable_only_repoids_in_copied_files`` is
    set and pre-install copies exist); run the client swap; apply post-install
    tasks; locate the installed client files; remove non-client injected setup
    files.

    :param context_scratch: Scratch container context the swap is performed in.
    :type context_scratch: mounting.IsolatedActions
    :param rhui_info: RHUI info describing the source/target clients and setup.
    :type rhui_info: RHUIInfo
    :param target_version: Release version used for the swap and client queries.
    :type target_version: str
    :param skip_rhsm: Whether to skip subscription-manager related dnf flags.
    :type skip_rhsm: bool
    :raises StopActorExecutionError: When parsing the copied repofiles fails, when
        the client swap transaction fails, when applying the post-install file
        tasks fails, or when the installed client files cannot be located.
    """
    if not rhui_info:
        return

    setup = rhui_info.target_client_setup_info

    _run_preinstall_tasks(context_scratch, setup.preinstall_tasks)

    # When not bootstrapping, stop right after pre-install (no swap etc.).
    if not setup.bootstrap_target_client:
        return

    enable_only_repoids = set()
    has_preinstall_copies = bool(
        setup.preinstall_tasks and setup.preinstall_tasks.files_to_copy_into_overlay
    )
    if setup.enable_only_repoids_in_copied_files and has_preinstall_copies:
        enable_only_repoids = _parse_repoids_from_copied_files(setup.preinstall_tasks.files_to_copy_into_overlay)

    _swap_clients(context_scratch, rhui_info, target_version, skip_rhsm, enable_only_repoids)

    _run_postinstall_tasks(context_scratch, setup.postinstall_tasks)

    client_files = _find_rhui_client_files(
        context_scratch,
        rhui_info.target_client_pkg_names,
        get_major_version(target_version)
    )
    _remove_nonclient_injected_files(context_scratch, rhui_info, client_files)


def cleanup_injected_repofiles(context, rhui_info):
    """
    Clean up injected repofiles not owned by any rpm after the build.

    No-op when ``rhui_info`` is falsy or when there are no pre-install tasks. For
    each injected copy that is an existing ``.repo`` file: it is kept if an rpm
    owns it and deleted if none does, which prevents duplicate repoids in the built
    userspace. The caller invokes this only for cloud, only when
    ``bootstrap_target_client`` is false, after the leapp dnf plugin is installed
    and before subscription-manager container mode is set.

    :param context: Container context the cleanup is performed in.
    :type context: mounting.IsolatedActions
    :param rhui_info: RHUI info providing the pre-install copy tasks.
    :type rhui_info: RHUIInfo
    """
    if not rhui_info:
        return

    setup = rhui_info.target_client_setup_info
    if not setup.preinstall_tasks:
        return

    for dummy_src, dst in _sanitized_copy_files_iter(context, setup.preinstall_tasks.files_to_copy_into_overlay):
        if not dst.endswith('.repo') or not os.path.isfile(context.full_path(dst)):
            continue
        try:
            context.call(['rpm', '-qf', dst])
            owned = True
        except CalledProcessError:
            owned = False
        if not owned:
            api.current_logger().debug('Removing injected RHUI repofile not owned by any rpm: {}'.format(dst))
            context.remove(dst)
