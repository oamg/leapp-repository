"""
Cert and repository-file access for the freshly built target userspace.

Single responsibility: once the target userspace exists, make the source
system's trust anchors and repository configuration available inside it without
clobbering files the target packages own. Concretely: copy ``/etc/pki`` from the
source (decoupling its symlinks), refresh the CA trust store, copy the RHSM
configuration, and merge ``/etc/yum.repos.d`` while preserving any RPM-owned
repofiles already present in the container.

The ``/etc/pki`` symlink-decoupling logic (``_choose_copy_or_link``,
``_copy_symlinks``, ``_copy_decouple`` and ``_copy_certificates``) is a FROZEN
CARVE-OUT: it is reproduced here byte-for-byte and must not be edited. It carries
a known multi-hop-symlink bug (captured by an ``xfail`` characterization test)
that is intentionally out of scope for this redesign.

This module depends only on shared leapp libraries - nothing actor-side - so it
sits at the bottom of the actor's import DAG alongside ``layout``.
"""

import os

from leapp.libraries.common import mounting, rhsm
from leapp.libraries.stdlib import api, CalledProcessError, run


class BrokenSymlinkError(Exception):
    """Raised when we encounter a broken symlink where we weren't expecting it."""


def prep_repository_access(context, target_userspace):
    """
    Prepare repository access by copying all relevant certificates and configuration files to the userspace
    """
    _copy_certificates(context, target_userspace)
    _refresh_ca_trust(target_userspace)
    _copy_rhsm_config(context, target_userspace)
    _merge_repos_preserving_rpm_owned(context, target_userspace)


def _refresh_ca_trust(target_userspace):
    # NOTE(dkubek): context.call(['update-ca-trust']) seems to not be working.
    #               I am not really sure why. The changes to files are not
    #               being written to disk.
    run(["chroot", target_userspace, "/bin/bash", "-c", "su - -c update-ca-trust"])


def _copy_rhsm_config(context, target_userspace):
    if rhsm.skip_rhsm():
        return
    target_rhsm = os.path.join(target_userspace, 'etc', 'rhsm')
    run(['rm', '-rf', target_rhsm])
    context.copytree_from('/etc/rhsm', target_rhsm)


def _merge_repos_preserving_rpm_owned(context, target_userspace):
    """
    Replace the container's yum.repos.d with the one from scratch, keeping repofiles owned by an RPM.

    We cannot simply remove the target yum.repos.d and swap in the one from the
    scratch container we used to obtain the new DNF stack: although RHUI clients
    are installed in both containers, users can request packages that install
    additional repofiles into the target userspace which are not present in
    scratch. Such RPM-owned repofiles are detected, preserved across the swap,
    and restored afterwards.
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
    Return the list of file names inside dirpath owned by RPMs.

    The returned paths are relative to the dirpath.

    This is important e.g. in case of RHUI which installs specific repo files
    in the yum.repos.d directory.

    In case the pkgs param is None or empty, do not filter any specific rpms.
    Otherwise return filenames that are owned by any pkg in the given list.

    If the recursive param is set to True, all files owned by a package in the
    directory tree starting at dirpath are returned. Otherwise, only the
    files within dirpath are checked.
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
                relpath = os.path.relpath(os.path.join(root, filename), searchdir)
                file_list.append(relpath)
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
    Create directories with a file to copy the mode from.

    :param path: The directory path to create.
    :param mode_from: A file or directory whose mode we will copy to the
        newly created directory.
    :raises subprocess.CalledProcessError: mkdir or chmod fails. For instance,
        the directory already exists, the file to get permissions from does
        not exist, a parent directory does not exist.
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
    Determine whether to copy file contents or create a symlink depending on where the pointee resides.

    :param symlink: The source symlink to follow.  This must be an absolute path.
    :param srcdir: The root directory that every piece of content must be present in.
    :returns: A tuple of action and sourcefile.  Action is one of 'copy' or 'link' and means that
        the caller should either copy the sourcefile to the target location or create a symlink from
        the sourcefile to the target location.  sourcefile is the path to the file that should be
        the source of the operation.  It is either a real file outside of the srcdir hierarchy or
        a file (real, directory, symlink or otherwise) inside of the srcdir hierarchy.
    :raises ValueError: if the arguments are not correct
    :raises BrokenSymlinkError: if the symlink is invalid

    Determine whether the file pointed to by the symlink chain is within srcdir.  If it is within,
    then create a synlink that points from symlink to it.

    If it is not within, then walk the symlink chain until we find something that is within srcdir
    and return that. This means we will omit any symlinks that are outside of srcdir from
    the symlink chain.

    If we reach a real file and it is outside of srcdir, then copy the file instead.
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
    Copy file contents or create a symlink depending on where the pointee resides.

    :param symlinks_to_process: List of 2-tuples of (src_path, target_path).  Each src_path
        should be an absolute path to the symlink.  target_path is the path to where we
        need to create either a link or a copy.
    :param srcdir: The root directory that every piece of content must be present in.
    :raises ValueError: if the arguments are not correct
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
    Copy files inside of `srcdir` to `dstdir` while decoupling symlinks.

    What we mean by decoupling the `srcdir` is that any symlinks pointing
    outside the directory will be copied as regular files. This means that the
    directory will become independent from its surroundings with respect to
    symlinks. Any symlink (or symlink chains) within the directory will be
    preserved.

    .. warning::
        `dstdir` must already exist.
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
    Copy certificates from source system into the container, but preserve
    original ones

    Some certificates are already installed in the container and those are
    default certificates for the target OS, so we preserve these.

    We respect the symlink hierarchy of the source system within the /etc/pki
    folder. Dangling symlinks will be ignored.

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
