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
from leapp.libraries.common import repofileutils
from leapp.libraries.stdlib import api, CalledProcessError

_YUM_REPOS_D = '/etc/yum.repos.d'
# TODO?
_HIDDEN_SUFFIX = '.leapp-hidden'

# repoid substrings excluded from the client-repoid discovery repolist (§13 R2).
_EXCLUDED_REPOID_MARKERS = ('-source-', '-debug-', 'source')


def _copy_file_dst(copy_file):
    """Return the intended destination for a CopyFile (dst may be null → src)."""
    return copy_file.dst if copy_file.dst else copy_file.src


def _resolve_copy_target(context, copy_file):
    """
    R1 - copy-target path resolution.

    If the destination resolves to an existing directory in the container, the
    file lands at ``destination/basename(source)``; otherwise the destination
    path is used unchanged.
    """
    # FIXME: why this function at all? Check it better with the existing code
    dst = _copy_file_dst(copy_file)
    if os.path.isdir(context.full_path(dst)):
        return os.path.join(dst, os.path.basename(copy_file.src))
    return dst


def _ensure_parent_dir(context, dst):
    """Create the container-side parent directory of ``dst`` (OSError → hard stop)."""
    parent = os.path.dirname(context.full_path(dst))
    # FIXME: better would be context.makedirs instead; also changed behaviour
    try:
        if not os.path.isdir(parent):
            os.makedirs(parent)
    except OSError as e:
        raise StopActorExecutionError(
            message='Failed to create target userspace directories for RHUI.',
            details={'details': str(e)}
        )


def _run_preinstall_tasks(context, preinstall_tasks):
    """
    R3 - pre-install tasks into scratch: removals first, then host→container
    copies (with parent dirs created).
    """
    if not preinstall_tasks:
        return

    # FIXME: add logs
    for path in preinstall_tasks.files_to_remove:
        context.remove(path)

    for copy_file in preinstall_tasks.files_to_copy_into_overlay:
        # FIXME: this seems weird
        # think about the order.. - maybe update input data?...
        dst = _resolve_copy_target(context, copy_file)
        _ensure_parent_dir(context, dst)
        context.copy_to(copy_file.src, dst)


def _run_postinstall_tasks(context, postinstall_tasks):
    """
    R4 - post-install tasks inside the container: in-container copies to each
    destination (with parent dirs). Applied only after a successful swap.
    """
    if not postinstall_tasks:
        return

    for copy_file in postinstall_tasks.files_to_copy:
        # FIXME. same as above. note original script did not used `-a` option
        dst = _resolve_copy_target(context, copy_file)
        _ensure_parent_dir(context, dst)
        context.call(['cp', '-a', copy_file.src, dst])


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
    for copy_file in preinstall_tasks.files_to_copy_into_overlay:
        dst = _resolve_copy_target(context, copy_file)
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


def _parse_repoids_from_copied_files(context, rhui_info):
    """Parse repoids from the pre-install copied ``.repo`` files (parse fail → hard stop)."""
    # FIXME. just take it from orig code. this bad
    repoids = set()
    preinstall_tasks = rhui_info.target_client_setup_info.preinstall_tasks
    for copy_file in preinstall_tasks.files_to_copy_into_overlay:
        dst = _resolve_copy_target(context, copy_file)
        if not dst.endswith('.repo'):
            continue
        try:
            repofile = repofileutils.parse_repofile(context.full_path(dst))
        except Exception as e:  # noqa: E722; repofileutils raises InvalidRepoDefinition
            raise StopActorExecutionError(
                message='Failed to parse repositories for RHUI.',
                details={'details': str(e)}
            )
        for repo in repofile.data:
            repoids.add(repo.repoid)
    return repoids


def _swap_clients(context, rhui_info, target_major, releasever, skip_rhsm, enable_only_repoids):
    """
    Run the client swap via ``dnf shell`` (transaction: remove source clients →
    install target clients → run). Swap failure → hard stop.
    """
    # FIXME: reduce amount of params
    script_lines = []
    if rhui_info.src_client_pkg_names:
        script_lines.append('remove {}'.format(' '.join(rhui_info.src_client_pkg_names)))
    script_lines.append('install {}'.format(' '.join(rhui_info.target_client_pkg_names)))
    # TODO transaction run?
    script_lines.append('run')
    script_lines.append('')
    # TODO name & path
    # it would be nice to actually standardize paths on which we store such
    # files.
    script_path = '/leapp-rhui-swap.dnfsh'
    with context.open(script_path, 'w') as fobj:
        fobj.write('\n'.join(script_lines))

    cmd = ['dnf', 'shell', '-y']
    cmd += tus_constants.common_dnf_flags(target_major, releasever, skip_rhsm)
    if enable_only_repoids:
        cmd.append('--disablerepo=*')
        for repoid in sorted(enable_only_repoids):
            cmd.append('--enablerepo={}'.format(repoid))
    cmd.append(script_path)

    try:
        # TODO: update the logging handled; callback_raw=utils.logging_handler
        context.call(cmd)
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
        context.remove(script_path)


def _find_client_files(context, rhui_info, target_major):
    """Return files installed by the target client rpm(s) (none → hard stop)."""
    client_files = []
    for pkg in rhui_info.target_client_pkg_names:
        try:
            result = context.call(['rpm', '-ql', pkg], split=True)
        except CalledProcessError:
            continue
        client_files.extend(result['stdout'])

    if not client_files:
        raise StopActorExecutionError(
            message='Could not find the RHEL {} RHUI client rpm(s) needed to'
                    ' access the target content.'.format(target_major)
        )
    return client_files


def _remove_nonclient_injected_files(context, rhui_info, client_files):
    """
    Remove injected setup files whose container destination is not client-owned
    and whose source is not in ``files_supporting_client_operation`` (§13 R5).
    """
    setup = rhui_info.target_client_setup_info
    supporting = set(setup.files_supporting_client_operation)
    client_files = set(client_files)

    for copy_file in setup.preinstall_tasks.files_to_copy_into_overlay:
        dst = _resolve_copy_target(context, copy_file)
        if dst in client_files:
            continue
        if copy_file.src in supporting:
            continue
        context.remove(dst)


def perform_client_swap(context, rhui_info, target_major, releasever, skip_rhsm):
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
    _run_preinstall_tasks(context, setup.preinstall_tasks)

    # R5: when not bootstrapping, stop right after pre-install (no swap etc.).
    if not setup.bootstrap_target_client:
        return

    # TODO: update the name?
    enable_only_repoids = set()
    has_preinstall_copies = bool(
        setup.preinstall_tasks and setup.preinstall_tasks.files_to_copy_into_overlay
    )
    if setup.enable_only_repoids_in_copied_files and has_preinstall_copies:
        # FIXME: needs to be changed - give it just related content instead of whole msg
        enable_only_repoids = _parse_repoids_from_copied_files(context, rhui_info)

    _swap_clients(context, rhui_info, target_major, releasever, skip_rhsm, enable_only_repoids)

    # R4
    _run_postinstall_tasks(context, setup.postinstall_tasks)

    # FIXME: different behaviour from the original.
    client_files = _find_client_files(context, rhui_info, target_major)
    _remove_nonclient_injected_files(context, rhui_info, client_files)


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

    for copy_file in setup.preinstall_tasks.files_to_copy_into_overlay:
        dst = _resolve_copy_target(context, copy_file)
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
