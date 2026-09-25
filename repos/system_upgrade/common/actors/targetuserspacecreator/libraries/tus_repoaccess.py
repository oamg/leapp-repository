"""
Make the source system's certificates and repository configuration available in the target userspace.

Once the target userspace has been built, this module copies the source
system's trust anchors and repository configuration into it without overwriting
files that the target packages own. Specifically it:

* copies ``/etc/pki`` from the source system, decoupling its symlinks so that
  the resulting tree is self-contained;
* refreshes the CA trust store inside the container;
* copies the RHSM configuration (unless RHSM handling is skipped);
* merges ``/etc/yum.repos.d`` while preserving any RPM-owned repofiles that
  already exist in the container.

The ``/etc/pki`` symlink-decoupling helpers (``_choose_copy_or_link``,
``_copy_symlinks``, ``_copy_decouple`` and ``_copy_certificates``) are kept
unchanged on purpose. They carry a known bug when handling multi-hop RPM-owned
symlinks (covered by an xfail characterization test) that is deliberately left
out of scope.

This module depends only on shared leapp libraries, so it has no actor-side
imports.
"""

import os

from leapp.libraries.common import mounting, rhsm
from leapp.libraries.stdlib import api, CalledProcessError, run


class BrokenSymlinkError(Exception):
    """Raised when a broken symlink is encountered where a valid one was expected."""


def prep_repository_access(context, target_userspace):
    """
    Copy the source system's certificates and repository configuration into the target userspace.

    Copies the trust anchors from ``/etc/pki``, refreshes the CA trust store,
    copies the RHSM configuration and merges ``/etc/yum.repos.d`` while keeping
    the RPM-owned repofiles that already exist in the container.

    :param context: Mounting context giving access to the source system tree.
    :type context: mounting.IsolatedActions
    :param target_userspace: Filesystem path to the target userspace container.
    :type target_userspace: str
    :raises CalledProcessError: If any of the underlying commands (file copies,
        trust-store refresh, moves or removals) fails.
    :raises ValueError: If a symlink processed while decoupling ``/etc/pki`` is
        not given as an absolute path.
    :raises RuntimeError: If the internal symlink-copy helper reports an unknown
        action (programming error).
    """
    _copy_certificates(context, target_userspace)
    _refresh_ca_trust(target_userspace)
    _copy_rhsm_config(context, target_userspace)
    _merge_repos_preserving_rpm_owned(context, target_userspace)


def _refresh_ca_trust(target_userspace):
    """
    Refresh the CA trust store inside the target userspace.

    Runs ``update-ca-trust`` through a login shell in a chroot of the target
    userspace so that the newly copied certificates take effect.

    :param target_userspace: Filesystem path to the target userspace container.
    :type target_userspace: str
    :raises CalledProcessError: If the ``update-ca-trust`` command fails.
    """
    # NOTE(dkubek): context.call(['update-ca-trust']) seems to not be working.
    #               I am not really sure why. The changes to files are not
    #               being written to disk.
    run(["chroot", target_userspace, "/bin/bash", "-c", "su - -c update-ca-trust"])


def _copy_rhsm_config(context, target_userspace):
    """
    Copy the source system's RHSM configuration into the target userspace.

    Does nothing when RHSM handling is skipped. Otherwise it removes any
    existing ``/etc/rhsm`` in the container and replaces it with a copy from the
    source system.

    :param context: Mounting context giving access to the source system tree.
    :type context: mounting.IsolatedActions
    :param target_userspace: Filesystem path to the target userspace container.
    :type target_userspace: str
    :raises CalledProcessError: If removing the existing ``/etc/rhsm`` directory
        fails.
    """
    if rhsm.skip_rhsm():
        return
    target_rhsm = os.path.join(target_userspace, 'etc', 'rhsm')
    run(['rm', '-rf', target_rhsm])
    context.copytree_from('/etc/rhsm', target_rhsm)


def _merge_repos_preserving_rpm_owned(context, target_userspace):
    """
    Replace the container's ``yum.repos.d`` with the scratch one, keeping RPM-owned repofiles.

    The target ``yum.repos.d`` cannot simply be discarded: although RHUI clients
    are installed in both containers, requested packages may install extra
    repofiles into the target userspace that are absent from the scratch
    container used to obtain the new DNF stack. Such RPM-owned repofiles are
    detected before the swap and restored afterwards; in between, the scratch
    ``yum.repos.d`` (carrying the new DNF stack and RHUI client) is copied in.

    :param context: Mounting context giving access to the scratch container tree.
    :type context: mounting.IsolatedActions
    :param target_userspace: Filesystem path to the target userspace container.
    :type target_userspace: str
    :raises CalledProcessError: If moving, copying or removing the repository
        directories or files fails.
    """
    target_etc = os.path.join(target_userspace, 'etc')
    target_yum_repos_d = os.path.join(target_etc, 'yum.repos.d')
    backup_yum_repos_d = os.path.join(target_etc, 'yum.repos.d.backup')

    # Detect files that are owned by some RPM - these cannot be deleted
    with mounting.NspawnActions(base_dir=target_userspace) as target_context:
        files_owned_by_rpms = _get_files_owned_by_rpms(target_context, '/etc/yum.repos.d')

    # Backup the target yum.repos.d so we can always copy the files installed by some RPM back into yum.repos.d
    # when we modify it
    run(['mv', target_yum_repos_d, backup_yum_repos_d])

    # Copy the yum.repos.d from scratch - preserve any custom repositories. No need to clean-up old RHUI clients,
    # we swap them for the new RHUI client in scratch (so the old one is not installed).
    context.copytree_from('/etc/yum.repos.d', target_yum_repos_d)

    # Copy back files owned by some RPM
    for fname in files_owned_by_rpms:
        api.current_logger().debug('Copy the backed up repo file: {}'.format(fname))
        run(['mv', os.path.join(backup_yum_repos_d, fname), os.path.join(target_yum_repos_d, fname)])

    # Cleanup - remove the backed up dir
    run(['rm', '-rf', backup_yum_repos_d])


def _get_files_owned_by_rpms(context, dirpath, pkgs=None, recursive=False):
    """
    Return the names of files inside ``dirpath`` that are owned by an installed RPM.

    The returned paths are relative to ``dirpath``. This matters for example
    with RHUI, which installs specific repo files into the ``yum.repos.d``
    directory.

    When ``pkgs`` is ``None`` or empty, every RPM-owned file is returned.
    Otherwise only files owned by one of the listed packages are returned.

    When ``recursive`` is ``True``, the whole directory tree rooted at
    ``dirpath`` is scanned (the ``directory-hash`` subtree is skipped for
    performance, as it is not relevant to the upgrade). Otherwise only the
    direct entries of ``dirpath`` are checked.

    :param context: Mounting context used to resolve paths and run ``rpm`` queries.
    :type context: mounting.NspawnActions
    :param dirpath: Directory to inspect, given as a path inside the context.
    :type dirpath: str
    :param pkgs: Optional iterable of package names used to filter the results.
    :type pkgs: Iterable[str]
    :param recursive: Whether to scan the directory tree recursively.
    :type recursive: bool
    :returns: File names (relative to ``dirpath``) owned by a matching RPM.
    :rtype: List[str]
    """

    files_owned_by_rpms = []

    file_list = []
    searchdir = context.full_path(dirpath)
    if recursive:
        for root, _, files in os.walk(searchdir):
            if '/directory-hash' in root:
                # tl;dr; for the performance improvement
                # The directory has been relatively recently added to ca-certificates
                # rpm on EL 9+ systems and the content does not seem to be important
                # for the IPU process. Also, it contains high number of files and
                # their processing floods the output and slows down IPU.
                # So skipping it entirely.
                # This is updated solution that we drop originally: 60f500e59bb92
                api.current_logger().debug('SKIP files in the {} directory: Not important for the IPU.'.format(root))
                continue
            for filename in files:
                relpath_to_searchdir = os.path.relpath(os.path.join(root, filename), searchdir)
                file_list.append(relpath_to_searchdir)
    else:
        file_list = os.listdir(searchdir)

    for fname in file_list:
        try:
            result = context.call(['rpm', '-qf', os.path.join(dirpath, fname)])
        except CalledProcessError:
            api.current_logger().debug('SKIP the {} file: not owned by any rpm'.format(fname))
            continue
        if pkgs and not [pkg for pkg in pkgs if pkg in result['stdout']]:
            api.current_logger().debug('SKIP the {} file: not owned by any searched rpm'.format(fname))
            continue
        api.current_logger().debug('Found the file owned by an rpm: {}.'.format(fname))
        files_owned_by_rpms.append(fname)

    return files_owned_by_rpms


def _mkdir_with_copied_mode(path, mode_from):
    """
    Create a directory and copy its mode from an existing reference path.

    The directory (and any missing parents) is first created with the most
    restrictive permissions and then its mode is set to match ``mode_from``.

    :param path: The directory path to create.
    :type path: str
    :param mode_from: A file or directory whose mode is copied onto the newly
        created directory.
    :type mode_from: str
    :raises CalledProcessError: If ``mkdir`` or ``chmod`` fails, for instance
        when ``mode_from`` does not exist.
    """
    # Create with maximally restrictive permissions
    run(['mkdir', '-m', '0', '-p', path])
    run(['chmod', '--reference={}'.format(mode_from), path])


# ---------------------------------------------------------------------------
# FROZEN CARVE-OUT - DO NOT EDIT
#
# The /etc/pki symlink-decoupling helpers below are reproduced verbatim from
# the original actor. They carry a known bug: the multi-hop RPM-owned symlink
# loop in _copy_certificates never advances its pointee, so such a symlink is
# misclassified as broken and skipped (see the xfail characterization test).
# Fixing that is intentionally out of scope for this redesign; these bodies
# must stay byte-for-byte identical.
# ---------------------------------------------------------------------------
def _choose_copy_or_link(symlink, srcdir):
    """
    Decide whether to copy a symlink's target contents or recreate it as a link.

    Follow the symlink chain starting at ``symlink``. If the chain reaches a
    target that lives inside ``srcdir``, return a ``link`` action together with a
    corrected link path (absolute or relative, matching the original link);
    symlinks pointing outside ``srcdir`` are skipped while walking the chain. If
    the chain ends at a real file or directory outside ``srcdir``, return a
    ``copy`` action with the path of that real file.

    :param symlink: The source symlink to follow. Must be an absolute path.
    :type symlink: str
    :param srcdir: The root directory that the content must reside in.
    :type srcdir: str
    :returns: A 2-tuple ``(action, sourcefile)`` where ``action`` is ``'copy'``
        or ``'link'`` and ``sourcefile`` is the path the caller should copy from
        or link to.
    :rtype: Tuple[str, str]
    :raises ValueError: If ``symlink`` is not an absolute path.
    :raises BrokenSymlinkError: If ``symlink`` is broken or forms a
        self-referential loop.
    """
    if not symlink.startswith('/'):
        raise ValueError('File{} must be an absolute path!'.format(symlink))

    # os.path.exists follows symlinks
    if not os.path.exists(symlink):
        raise BrokenSymlinkError('File {} is a broken symlink!'.format(symlink))

    # If srcdir is a symlink, then we need a name for it that we can compare
    # with other paths.
    canonical_srcdir = os.path.realpath(srcdir)

    pointee_as_abspath = symlink
    seen = set([pointee_as_abspath])

    # The goal of this while loop is to find the next link in a possible
    # symlink chain that either points to a symlink inside of srcdir or to
    # a file or directory that we can copy.
    while os.path.islink(pointee_as_abspath):
        # Advance pointee to the target of the previous link
        pointee = os.readlink(pointee_as_abspath)

        # Note: os.path.join()'s behaviour if the pointee is an absolute path
        # essentially ignores the first argument (which is what we want).
        pointee_as_abspath = os.path.normpath(os.path.join(os.path.dirname(pointee_as_abspath), pointee))

        # Make sure we aren't in a circular set of references.
        # On Linux, this should not happen as the os.path.exists() call
        # before the loop should catch it but we don't want to enter an
        # infinite loop if that code changes later.
        if pointee_as_abspath in seen:
            if symlink == pointee_as_abspath:
                error_msg = ('File {} is a broken symlink that references'
                             ' itself!'.format(pointee_as_abspath))
            else:
                error_msg = ('File {} references {} which is a broken symlink'
                             ' that references itself!'.format(symlink, pointee_as_abspath))

            raise BrokenSymlinkError(error_msg)

        seen.add(pointee_as_abspath)

        # To make comparisons, we need to resolve all symlinks in the directory
        # structure leading up to pointee.  However, we can't include pointee
        # itself otherwise it will resolve to the file that it points to in the
        # end (which would be wrong if pointee_filename is a symlink).
        canonical_pointee_dir, pointee_filename = os.path.split(pointee_as_abspath)
        canonical_pointee_dir = os.path.realpath(canonical_pointee_dir)

        if canonical_pointee_dir.startswith(canonical_srcdir):
            # Absolute path inside of the correct dir so we need to link to it
            # But we need to determine what the link path should be before
            # returning.

            # Construct a relative path that points from the symlinks directory
            # to the pointee.
            link_to = os.readlink(symlink)
            canonical_symlink_dir = os.path.realpath(os.path.dirname(symlink))
            relative_path = os.path.relpath(canonical_pointee_dir, canonical_symlink_dir)

            if link_to.startswith('/'):
                # The original symlink was an absolute path so we will set this
                # one to absolute too
                # Note: Because absolute paths are constructed inside of
                # srcdir, the relative path that we need to join here has to be
                # relative to srcdir, not the directory that the symlink is
                # being created in.
                relative_to_srcdir = os.path.relpath(canonical_pointee_dir, canonical_srcdir)
                corrected_path = os.path.normpath(os.path.join(srcdir, relative_to_srcdir, pointee_filename))

            else:
                # If the original link is a relative link, then we want the new
                # link to be relative as well
                corrected_path = os.path.normpath(os.path.join(relative_path, pointee_filename))

            return ("link", corrected_path)

        # pointee is a symlink that points outside of the srcdir so continue to
        # the next symlink in the chain.

    # The file is not a link so copy it
    return ('copy', pointee_as_abspath)


def _copy_symlinks(symlinks_to_process, srcdir):
    """
    Process a list of symlinks, copying their contents or recreating them as links.

    For each entry the decision is delegated to the helper that follows the
    symlink chain: content whose ultimate target lies outside ``srcdir`` is
    copied, otherwise a corresponding link is created. Broken symlinks are logged
    and skipped.

    :param symlinks_to_process: Iterable of ``(src_path, target_path)`` tuples.
        ``src_path`` must be an absolute path to the symlink; ``target_path`` is
        where the link or copy is created.
    :type symlinks_to_process: List[Tuple[str, str]]
    :param srcdir: The root directory that the content must reside in.
    :type srcdir: str
    :raises ValueError: If a processed symlink is not an absolute path.
    :raises RuntimeError: If the internal decision helper returns an unknown
        action (programming error).
    :raises CalledProcessError: If copying the file or creating the link fails.
    """
    for source_linkpath, target_linkpath in symlinks_to_process:
        try:
            action, source_path = _choose_copy_or_link(source_linkpath, srcdir)
        except BrokenSymlinkError as e:
            # Skip and report broken symlinks
            api.current_logger().warning('{} Will not copy the file!'.format(str(e)))
            continue

        if action == "copy":
            # Note: source_path could be a directory, so '-a' or '-r' must be
            # given to cp.
            run(['cp', '-a', source_path, target_linkpath])
        elif action == 'link':
            run(["ln", "-s", source_path, target_linkpath])
        else:
            # This will not happen unless _copy_or_link() has a bug.
            raise RuntimeError("Programming error: _copy_or_link() returned an unknown action:{}".format(action))


def _copy_decouple(srcdir, dstdir):
    """
    Copy ``srcdir`` into ``dstdir`` while decoupling symlinks that point outside ``srcdir``.

    Decoupling means that any symlink (or symlink chain) leaving ``srcdir`` is
    materialised as a regular copy of its target, so the resulting tree does not
    depend on anything outside itself. Symlinks that stay within ``srcdir`` are
    preserved as links. Directories are recreated with the same mode as their
    source.

    :param srcdir: Directory tree to copy from.
    :type srcdir: str
    :param dstdir: Destination directory, which must already exist.
    :type dstdir: str
    :raises ValueError: If a symlink encountered during the walk is not an
        absolute path.
    :raises RuntimeError: If the internal symlink-copy helper returns an unknown
        action (programming error).
    :raises CalledProcessError: If creating a directory, copying a file or
        creating a link fails.

    .. warning::
        ``dstdir`` must already exist.
    """
    for root, directories, files in os.walk(srcdir):
        # relative path from srcdir because srcdir is replaced with dstdir for
        # the copy.
        relpath = os.path.relpath(root, srcdir)

        # Create all directories with proper permissions for security
        # reasons (Putting private data into directories that haven't had their
        # permissions set appropriately may leak the private information.)
        symlinks_to_process = []
        for directory in directories:
            source_dirpath = os.path.join(root, directory)
            target_dirpath = os.path.join(dstdir, relpath, directory)

            # Defer symlinks until later because we may end up having to copy
            # the file contents and the directory may not exist yet.
            if os.path.islink(source_dirpath):
                symlinks_to_process.append((source_dirpath, target_dirpath))
                continue

            _mkdir_with_copied_mode(target_dirpath, source_dirpath)

        # Link or create all directories that were pointed to by symlinks and
        # then reset symlinks_to_process for use by files.
        _copy_symlinks(symlinks_to_process, srcdir)
        symlinks_to_process = []

        for filename in files:
            source_filepath = os.path.join(root, filename)
            target_filepath = os.path.join(dstdir, relpath, filename)

            # Defer symlinks until later because we may end up having to copy
            # the file contents and the directory may not exist yet.
            if os.path.islink(source_filepath):
                symlinks_to_process.append((source_filepath, target_filepath))
                continue

            # Not a symlink so we can copy it now too
            run(['cp', '-a', source_filepath, target_filepath])

        _copy_symlinks(symlinks_to_process, srcdir)


def _copy_certificates(context, target_userspace):
    """
    Copy the source system's ``/etc/pki`` into the container, preserving package-owned files.

    The container already ships default certificates for the target OS that are
    owned by RPMs; those take precedence and are preserved. The source
    ``/etc/pki`` is copied in with its internal symlink hierarchy decoupled, then
    the RPM-owned files from the original container tree are restored on top.
    Dangling symlinks among the restored files are logged and skipped.

    :param context: Mounting context giving access to the source system tree.
    :type context: mounting.IsolatedActions
    :param target_userspace: Filesystem path to the target userspace container.
    :type target_userspace: str
    :raises CalledProcessError: If backing up, copying or removing files fails.
    :raises ValueError: If a symlink processed while decoupling is not an
        absolute path.
    :raises RuntimeError: If the internal symlink-copy helper returns an unknown
        action (programming error).
    """

    target_pki = os.path.join(target_userspace, 'etc', 'pki')
    backup_pki = os.path.join(target_userspace, 'etc', 'pki.backup')

    with mounting.NspawnActions(base_dir=target_userspace) as target_context:
        files_owned_by_rpms = _get_files_owned_by_rpms(target_context, '/etc/pki', recursive=True)
        api.current_logger().debug('Files owned by rpms: {}'.format(' '.join(files_owned_by_rpms)))

    # Backup container /etc/pki
    run(['mv', target_pki, backup_pki])

    # _copy_decouple() requires we create the target_pki directory here because we don't know
    # the mode inside of _copy_decouple().
    _mkdir_with_copied_mode(target_pki, backup_pki)

    # Copy source /etc/pki to the container
    _copy_decouple('/etc/pki', target_pki)

    # Assertion: after running _copy_decouple(), no broken symlinks exist in /etc/pki in the container
    # So any broken symlinks created will be by the installed packages.

    # Recover installed packages as they always get precedence
    for filepath in files_owned_by_rpms:
        src_path = os.path.join(backup_pki, filepath)
        dst_path = os.path.join(target_pki, filepath)

        # Resolve and skip any broken symlinks
        is_broken_symlink = False
        pointee = None
        if os.path.islink(src_path):
            pointee = os.path.join(target_userspace, os.readlink(src_path)[1:])

            seen = set()
            while os.path.islink(pointee):
                # The symlink points to a path relative to the target userspace so
                # we need to readjust it
                pointee = os.path.join(target_userspace, os.readlink(src_path)[1:])
                if not os.path.exists(pointee) or pointee in seen:
                    is_broken_symlink = True

                    # The path original path of the broken symlink in the container
                    report_path = os.path.join(target_pki, os.path.relpath(src_path, backup_pki))
                    api.current_logger().warning(
                            'File {} is a broken symlink! Will not copy!'.format(report_path))
                    break

                seen.add(pointee)

        if is_broken_symlink:
            continue

        # Cleanup conflicting files
        run(['rm', '-rf', dst_path])

        # Ensure destination exists
        parent_dir = os.path.dirname(dst_path)
        run(['mkdir', '-p', parent_dir])

        # Copy the new file
        run(['cp', '-R', '--preserve=all', src_path, dst_path])

    run(['rm', '-rf', backup_pki])
