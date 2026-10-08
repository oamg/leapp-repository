"""
RHUI (cloud) client-swap logic for the ``targetuserspacecreator`` actor - the
R1-R7 acceptance gate from §13.

The whole module is a no-op when no ``RHUIInfo`` is consumed (``rhui_info`` falsy):
every public entry point guards on it. Otherwise it swaps the source RHUI client
rpm(s) for the target client rpm(s) inside the scratch container (via
``dnf shell``), applies the pre/post-install file tasks, and leaves
``/etc/yum.repos.d`` consistent. Every RHUI failure surfaces as a hard stop -
never a silent continue.

Leaf module: imports shared leapp libraries, ``tus_constants`` and the frozen
``tus_repoaccess`` (only its RPM-ownership helper). It must never be imported by
``tus_repoaccess``.
"""

import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_constants, tus_repoaccess
from leapp.libraries.common import repofileutils, utils
from leapp.libraries.common.config.version import get_major_version
from leapp.libraries.stdlib import api, CalledProcessError

_YUM_REPOS_D = '/etc/yum.repos.d'
# TODO?
_HIDDEN_SUFFIX = '.leapp-hidden'

# repoid substrings excluded from the client-repoid discovery repolist (§13 R2).
_EXCLUDED_REPOID_MARKERS = ('-source-', '-debug-', 'source')


def _copy_file_dst(copy_file):
    """Return the intended destination for a CopyFile (dst may be null → src)."""
    # TODO(pstodulk): peform the action in data input loading??
    return copy_file.dst if copy_file.dst else copy_file.src


def _resolve_copy_target(context, copy_file):
    """
    R1 - copy-target path resolution.

    If the destination resolves to an existing directory in the container, the
    file lands at ``destination/basename(source)``; otherwise the destination
    path is used unchanged.
    """
    dst = _copy_file_dst(copy_file)
    if os.path.isdir(context.full_path(dst)):
        return os.path.join(dst, os.path.basename(copy_file.src))
    return dst


def _sanitized_copy_files_iter(context, copy_files):
    """
    Create sanitized iterator over list of CopyFiles.

    Return tuple src, dst for each CopyFile object in the list. dst is resolved
    to reflect the expected dst path:
      * fill it when dst is empty - path should be same as src then
      * if dst points to a dir, return path dst/fname

    The resulting list is sorted by the destination path. Note that at this
    moment there is no copy of dirs in this module, so it should not be a problem,
    but we will want to apply this on other places possibly as well, and probably
    it's better to be a little bit more defensive as we do not know what will be
    in future.
    """
    # NOTE: written sort this way to not affect input objects; as we do not
    # expect this to be a long list, it's ok
    for cfile in sorted(copy_files, key=lambda x: _resolve_copy_target(context, x)):
        yield cfile.src, _resolve_copy_target(context, cfile)


def _run_preinstall_tasks(context_scratch, preinstall_tasks):
    """
    R3 - pre-install tasks into scratch: removals first, then host→container
    copies (with parent dirs created).
    """
    if not preinstall_tasks:
        api.current_logger().debug('No RHUI preinstall tasks - skipping.')
        return

    api.current_logger().debug('Applying RHUI preinstall tasks.')
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


def _run_postinstall_tasks(context_scratch, postinstall_tasks):
    """
    R4 - post-install tasks inside the container: in-container copies to each
    destination (with parent dirs). Applied only after a successful swap.
    """
    if not postinstall_tasks:
        api.current_logger().debug('No RHUI postinstall tasks - skipping.')
        return

    api.current_logger().debug('Applying RHUI postinstall tasks.')
    for src, dst in _sanitized_copy_files_iter(context_scratch, postinstall_tasks.files_to_copy):
        api.current_logger().debug(
            ' -- Copying {0} to {1} (inside the scratch container).'
            .format(src, dst)
        )
        context_scratch.makedirs(os.path.dirname(dst), exists_ok=True)
        # NOTE: Note the use of CP instead of `copy_to` function is esential
        # as this action is designed to be performed inside the scratch
        # container context - so all paths are ment to be valid inside the container.
        # See the TargetRHUIPostInstallTasks model.
        context_scratch.call(['cp', src, dst])


def _list_repofiles(context):
    """Return the basenames of all ``*.repo`` files in the container's yum.repos.d."""
    repos_dir = context.full_path(_YUM_REPOS_D)
    if not os.path.isdir(repos_dir):
        return []
    return [name for name in os.listdir(repos_dir) if name.endswith('.repo')]


def _client_owned_repofiles(context, rhui_info):
    """
    Repofiles owned by the target RHUI client rpm(s).

    When ``bootstrap_target_client`` is false, no files are treated as
    client-owned (§13 R2).
    """
    if not rhui_info.target_client_setup_info.bootstrap_target_client:
        return set()
    # FIXME old code used rpm -ql, check if that's better fit
    return set(tus_repoaccess._get_files_owned_by_rpms(
        context, _YUM_REPOS_D, pkgs=rhui_info.target_client_pkg_names))


def _setup_copied_repofiles(context, rhui_info):
    """Basenames of the ``*.repo`` files injected by the pre-install copy tasks."""
    setup_copied = set()
    preinstall_tasks = rhui_info.target_client_setup_info.preinstall_tasks
    if not preinstall_tasks:
        return setup_copied
    for dummy_src, dst in _sanitized_copy_files_iter(context, preinstall_tasks.files_to_copy_into_overlay):
        if dst.endswith('.repo'):
            setup_copied.add(os.path.basename(dst))
    return setup_copied


def _hide_repofiles(context, filenames):
    """Rename the given repofiles out of the way; return list of (hidden, original)."""
    hidden = []
    for name in filenames:
        original = os.path.join(_YUM_REPOS_D, name)
        hidden_path = original + _HIDDEN_SUFFIX
        context.call(['mv', original, hidden_path])
        hidden.append((hidden_path, original))
    return hidden


def _restore_repofiles(context, hidden):
    """Restore every previously hidden repofile back to its original name."""
    for hidden_path, original in hidden:
        # FIXME os.rename
        context.call(['mv', hidden_path, original])


def _repolist_repoids(context):
    """Run ``dnf repolist`` and return the enabled repoids, excluding source/debug."""
    # FIXME this was done better in the old version, e.g. filtering using --(enable|disable)repo
    try:
        result = context.call(['dnf', 'repolist', '--enabled', '--quiet'], split=True)
    except CalledProcessError as e:
        raise StopActorExecutionError(
            message='Failed to retrieve repoids provided by target RHUI clients.',
            details={'details': str(e)}
        )

    repoids = set()
    for line in result['stdout']:
        line = line.strip()
        # FIXME this probably doesn't work, should be Repo-id, we should redo the function using old code probably
        if not line or line.lower().startswith('repo id'):
            continue
        repoid = line.split()[0]
        if any(marker in repoid for marker in _EXCLUDED_REPOID_MARKERS):
            continue
        repoids.add(repoid)
    return repoids


def discover_client_exposed_repoids(context, rhui_info):
    """
    R2 - discover the repoids exposed by the RHUI clients, leaving
    ``/etc/yum.repos.d`` byte-identical.

    Hides "foreign" repofiles (all ``*.repo`` minus client-owned minus
    setup-copied), runs ``dnf repolist`` with only client+setup repos visible,
    and restores every hidden file whether the repolist succeeds or fails.
    """
    if not rhui_info:
        return set()

    all_repofiles = set(_list_repofiles(context))
    keep_visible = _client_owned_repofiles(context, rhui_info) | _setup_copied_repofiles(context, rhui_info)
    foreign = all_repofiles - keep_visible

    hidden = []
    try:
        hidden = _hide_repofiles(context, foreign)
        return _repolist_repoids(context)
    finally:
        _restore_repofiles(context, hidden)


def _parse_repoids_from_copied_files(copy_files):
    """
    Parse repoids from the pre-install copied ``.repo`` files.

    Note the function assumes:

        * sources of repofiles have the .repo suffix (no rename of filenames
          planned for copying)
        * files were copied correctly
        * multiple sources does not point to the same destination
          (so destination is not replaced several times by preinstall tasks)

    Under these conditions, it's safe to parse repofiles from their original
    paths.
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
    Run the client swap via ``dnf shell`` (transaction: remove source clients →
    install target clients → run). Swap failure → hard stop.
    """
    # FIXME: reduce amount of params
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
        # TODO: update the logging handled; callback_raw=utils.logging_handler
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


def _find_rhui_client_files(context_scratch, pkgs, target_major_version):
    """Return files installed by the target client rpm(s) (none → hard stop)."""
    cmd = ['rpm', '-ql'] + pkgs
    try:
        rpm_query_result = context_scratch.call(cmd, split=True)
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

    return set(rpm_query_result['stdout'])


def _remove_nonclient_injected_files(context_scratch, rhui_info, client_files):
    """
    Remove injected setup files whose container destination is not client-owned
    and whose source is not in ``files_supporting_client_operation`` (§13 R5).
    """
    setup = rhui_info.target_client_setup_info
    supporting = set(setup.files_supporting_client_operation)

    for src, dst in _sanitized_copy_files_iter(context_scratch, setup.preinstall_tasks.files_to_copy_into_overlay):
        if dst in client_files or src in supporting:
            continue
        context_scratch.remove(dst)


def perform_client_swap(context_scratch, rhui_info, target_version, skip_rhsm):
    """
    R5 - orchestrate the whole RHUI client swap inside the scratch container.

    No-op when ``rhui_info`` is falsy. Order: pre-install tasks; early return if
    ``bootstrap_target_client`` is false; restrict-to-copied-repoids (if the
    toggle is set and pre-install copies exist); the client swap; post-install
    tasks; locate installed client files; remove non-client injected setup files.
    """
    if not rhui_info:
        return

    setup = rhui_info.target_client_setup_info

    # R3
    _run_preinstall_tasks(context_scratch, setup.preinstall_tasks)

    # R5: when not bootstrapping, stop right after pre-install (no swap etc.).
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
    R6 - post-build injected-repofile cleanup.

    For each injected copy that is an existing ``.repo`` file: keep it if an RPM
    owns it, delete it if none does (prevents duplicate repoids in the built
    userspace). The caller (§13 R7) invokes this only for cloud, only when
    ``bootstrap_target_client`` is false, after the leapp dnf plugin is installed
    and before subscription-manager container mode is set.
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
