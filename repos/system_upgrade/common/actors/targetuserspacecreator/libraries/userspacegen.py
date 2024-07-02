import itertools
import os
import re
import shutil

from leapp import reporting
from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.actor import constants
from leapp.libraries.common import dnfplugin, mounting, overlaygen, repofileutils, rhsm, utils
from leapp.libraries.common.config import get_env, get_product_type
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.common.gpg import get_path_to_gpg_certs, is_nogpgcheck_set
from leapp.libraries.stdlib import api, CalledProcessError, config, run
from leapp.models import RequiredTargetUserspacePackages  # deprecated
from leapp.models import TMPTargetRepositoriesFacts  # deprecated all the time
from leapp.models import (
    CustomTargetRepositoryFile,
    PkgManagerInfo,
    RepositoriesFacts,
    RHSMInfo,
    RHUIInfo,
    StorageInfo,
    TargetOSInstallationImage,
    TargetRepositories,
    TargetUserSpaceInfo,
    TargetUserSpacePreupgradeTasks,
    UsedTargetRepositories,
    UsedTargetRepository,
    XFSPresence
)
from leapp.utils.deprecation import suppress_deprecation

# TODO: "refactor" (modify) the library significantly
# The current shape is really bad and ineffective (duplicit parsing
# of repofiles). The library is doing 3 (5) things:
# # (0.) consume process input data
# # 1. prepare the first container, to be able to obtain repositories for the
# #    target system (this is extra neededwhen rhsm is used, but not reason to
# #    do such thing only when rhsm is used. Be persistent here
# # 2. gather target repositories that should AND can be used
# #    - basically here is the main thing that is PITA; I started
# #      the refactoring but realized that it needs much more changes because
# #      of RHSM...
# # 3. create the target userspace bootstrap
# # (4.) produce messages with the data
#
# Because of the lack of time, I am extending the current bad situation,
# but after the release, the related code should be really refactored.
# It would be probably ideal, if this and other actors in the current and the
# next phase are modified properly and we could create inhibitors in the check
# phase and keep everything on the report. But currently it seems it doesn't
# worth to invest so much energy into it. So let's just make this really
# readable (includes split of the functionality into several libraries)
# and do not mess.
# Issue: #486

PROD_CERTS_FOLDER = 'prod-certs'
PERSISTENT_PACKAGE_CACHE_DIR = '/var/lib/leapp/persistent_package_cache'
DEDICATED_LEAPP_PART_URL = 'https://access.redhat.com/solutions/7011704'


def _check_deprecated_rhsm_skip():
    # we do not plan to cover this case by tests as it is purely
    # devel/testing stuff, that becomes deprecated now
    # just log the warning now (better than nothing?); deprecation process will
    # be specified in close future
    if get_env('LEAPP_DEVEL_SKIP_RHSM', '0') == '1':
        api.current_logger().warning(
            'The LEAPP_DEVEL_SKIP_RHSM has been deprecated. Use'
            ' LEAPP_NO_RHSM instead or use the --no-rhsm option for'
            ' leapp. as well custom repofile has not been defined.'
            ' Please read documentation about new "skip rhsm" solution.'
        )


class BrokenSymlinkError(Exception):
    """Raised when we encounter a broken symlink where we weren't expecting it."""


class _InputData(object):
    def __init__(self):
        self._consume_data()

    @suppress_deprecation(RequiredTargetUserspacePackages)
    def _consume_data(self):
        """
        Wrapper function to consume majority input data.

        It doesn't consume TargetRepositories, which are consumed in the
        own function.
        """
        self.packages = {'dnf', 'dnf-command(config-manager)', 'util-linux'}
        self.files = []
        _cftuples = set()

        def _update_files(copy_files):
            # add just uniq CopyFile objects to omit duplicate copying of files
            for cfile in copy_files:
                cftuple = (cfile.src, cfile.dst)
                if cftuple not in _cftuples:
                    _cftuples.add(cftuple)
                    self.files.append(cfile)

        for task in api.consume(TargetUserSpacePreupgradeTasks):
            self.packages.update(task.install_rpms)
            _update_files(task.copy_files)

        for message in api.consume(RequiredTargetUserspacePackages):
            self.packages.update(message.packages)

        # Get the RHSM information (available repos, attached SKUs, etc.) of the source system
        self.rhsm_info = next(api.consume(RHSMInfo), None)
        self.rhui_info = next(api.consume(RHUIInfo), None)
        if not self.rhsm_info and not rhsm.skip_rhsm():
            api.current_logger().warning('Could not receive RHSM information - Is this system registered?')
            raise StopActorExecution()
        if rhsm.skip_rhsm() and self.rhsm_info:
            # this should not happen. if so, raise an error as something in
            # other actors is wrong really
            raise StopActorExecutionError("RHSM is not handled but the RHSMInfo message has been produced.")

        self.custom_repofiles = list(api.consume(CustomTargetRepositoryFile))
        self.xfs_info = next(api.consume(XFSPresence), XFSPresence())
        self.storage_info = next(api.consume(StorageInfo), None)
        if not self.storage_info:
            raise StopActorExecutionError('No storage info available cannot proceed.')


def _restore_persistent_package_cache(userspace_dir):
    if get_env('LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE', None) == '1':
        if not os.path.exists(PERSISTENT_PACKAGE_CACHE_DIR):
            return
        dst_cache = os.path.join(userspace_dir, 'var', 'cache', 'dnf')
        if os.path.exists(dst_cache):
            run(['rm', '-rf', dst_cache])
        shutil.move(PERSISTENT_PACKAGE_CACHE_DIR, dst_cache)
    # We always want to remove the persistent cache here to unclutter the system
    run(['rm', '-rf', PERSISTENT_PACKAGE_CACHE_DIR])


def _backup_to_persistent_package_cache(userspace_dir):
    if get_env('LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE', None) == '1':
        # Clean up any dead bodies, just in case
        run(['rm', '-rf', PERSISTENT_PACKAGE_CACHE_DIR])
        src_cache = os.path.join(userspace_dir, 'var', 'cache', 'dnf')
        if os.path.exists(src_cache):
            shutil.move(src_cache, PERSISTENT_PACKAGE_CACHE_DIR)


def _import_gpg_keys(context, install_root_dir, target_major_version):
    certs_path = get_path_to_gpg_certs()
    # Import the RHEL X+1 GPG key to be able to verify the installation of initial packages
    try:
        # Import also any other keys provided by the customer in the same directory
        for certname in os.listdir(certs_path):
            cmd = ['rpm', '--root', install_root_dir, '--import', os.path.join(certs_path, certname)]
            context.call(cmd, callback_raw=utils.logging_handler)
    except CalledProcessError as exc:
        raise StopActorExecutionError(
            message=(
                'Unable to import GPG certificates to install RHEL {} userspace packages.'
                .format(target_major_version)
            ),
            details={'details': str(exc), 'stderr': exc.stderr}
        )


def _handle_transaction_err_msg_size_old(err):
    # NOTE(pstodulk): This is going to be removed in future!

    article_section = 'Generic case'
    xfs_info = next(api.consume(XFSPresence), XFSPresence())
    if xfs_info.present and xfs_info.without_ftype:
        article_section = 'XFS ftype=0 case'

    message = ('There is not enough space on the file system hosting /var/lib/leapp directory '
               'to extract the packages.')
    details = {'hint': "Please follow the instructions in the '{}' section of the article at: "
                       "link: https://access.redhat.com/solutions/5057391".format(article_section)}

    raise StopActorExecutionError(message=message, details=details)


def _handle_transaction_err_msg_size(err):
    if get_env('LEAPP_OVL_LEGACY', '0') == '1':
        _handle_transaction_err_msg_size_old(err)
        return  # not needed actually as the above function raises error, but for visibility
    NO_SPACE_STR = 'more space needed on the'

    # Disk Requirements:
    #   At least <size> more space needed on the <path> filesystem.
    #
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
        .format(size_str, DEDICATED_LEAPP_PART_URL)
    )
    # we do not want to confuse customers by the orig msg speaking about
    # missing space on '/'. Skip the Disk Requirements section.
    # The information is part of the hint.
    details = {'hint': hint}

    raise StopActorExecutionError(message=message, details=details)


def prepare_target_userspace(context, userspace_dir, enabled_repos, packages):
    """
    Implement the creation of the target userspace.
    """
    _backup_to_persistent_package_cache(userspace_dir)

    run(['rm', '-rf', userspace_dir])
    _create_target_userspace_directories(userspace_dir)

    target_major_version = get_target_major_version()
    install_root_dir = '/el{}target'.format(target_major_version)
    with mounting.BindMount(source=userspace_dir, target=os.path.join(context.base_dir, install_root_dir.lstrip('/'))):
        _restore_persistent_package_cache(userspace_dir)
        if not is_nogpgcheck_set():
            _import_gpg_keys(context, install_root_dir, target_major_version)

        repos_opt = [['--enablerepo', repo] for repo in enabled_repos]
        repos_opt = list(itertools.chain(*repos_opt))
        cmd = ['dnf', 'install', '-y']
        if is_nogpgcheck_set():
            cmd.append('--nogpgcheck')
        cmd += [
            '--setopt=module_platform_id=platform:el{}'.format(target_major_version),
            '--setopt=keepcache=1',
            '--releasever', api.current_actor().configuration.version.target,
            '--installroot', install_root_dir,
            '--disablerepo', '*'
            ] + repos_opt + packages
        if config.is_verbose():
            cmd.append('-v')
        if rhsm.skip_rhsm():
            cmd += ['--disableplugin', 'subscription-manager']
        try:
            context.call(cmd, callback_raw=utils.logging_handler)
        except CalledProcessError as exc:
            message = 'Unable to install RHEL {} userspace packages.'.format(target_major_version)
            details = {'details': str(exc), 'stderr': exc.stderr}

            if 'more space needed on the' in exc.stderr:
                # The stderr contains this error summary:
                # Disk Requirements:
                #   At least <size> more space needed on the <path> filesystem.
                _handle_transaction_err_msg_size(exc)

            # If a proxy was set in dnf config, it should be the reason why dnf
            # failed since leapp does not support updates behind proxy yet.
            for manager_info in api.consume(PkgManagerInfo):
                if manager_info.configured_proxies:
                    details['details'] = (
                        "DNF failed to install userspace packages, likely due to the proxy "
                        "configuration detected in the YUM/DNF configuration file. "
                        "Make sure the proxy is properly configured in /etc/dnf/dnf.conf. "
                        "It's also possible the proxy settings in the DNF configuration file are "
                        "incompatible with the target system. A compatible configuration can be "
                        "placed in /etc/leapp/files/dnf.conf which, if present, will be used during "
                        "the upgrade instead of /etc/dnf/dnf.conf. "
                        "In such case the configuration will also be applied to the target system."
                    )

            # Similarly if a proxy was set specifically for one of the repositories.
            for repo_facts in api.consume(RepositoriesFacts):
                for repo_file in repo_facts.repositories:
                    if any(repo_data.proxy and repo_data.enabled for repo_data in repo_file.data):
                        details['details'] = (
                            "DNF failed to install userspace packages, likely due to the proxy "
                            "configuration detected in a repository configuration file."
                        )

            raise StopActorExecutionError(message=message, details=details)


def _query_rpm_for_pkg_files(context, pkgs):
    files_owned_by_rpm = set()
    rpm_query_result = context.call(['rpm', '-ql'] + pkgs, split=True)
    files_owned_by_rpm.update(rpm_query_result['stdout'])
    return files_owned_by_rpm


def _get_files_owned_by_rpms(context, dirpath, pkgs=None, recursive=False):
    """
    Return the list of file names inside dirpath owned by RPMs.

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
            for filename in files:
                relpath = os.path.relpath(os.path.join(root, filename), searchdir)
                # "directory-hash" files are not owned by any package and can dynamically
                # grow to a huge amount of files causing hitting open files limit
                if 'directory-hash' in relpath:
                    continue
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
            api.current_logger().debug('SKIP the {} file: not owned by any searched rpm:'.format(fname))
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


def _prep_repository_access(context, target_userspace):
    """
    Prepare repository access by copying all relevant certificates and configuration files to the userspace
    """
    target_etc = os.path.join(target_userspace, 'etc')
    target_yum_repos_d = os.path.join(target_etc, 'yum.repos.d')
    backup_yum_repos_d = os.path.join(target_etc, 'yum.repos.d.backup')

    _copy_certificates(context, target_userspace)
    # NOTE(dkubek): context.call(['update-ca-trust']) seems to not be working.
    #               I am not really sure why. The changes to files are not
    #               being written to disk.
    run(["chroot", target_userspace, "/bin/bash", "-c", "su - -c update-ca-trust"])

    if not rhsm.skip_rhsm():
        run(['rm', '-rf', os.path.join(target_etc, 'rhsm')])
        context.copytree_from('/etc/rhsm', os.path.join(target_etc, 'rhsm'))

    # NOTE: We cannot just remove the target yum.repos.d dir and replace it with yum.repos.d from the scratch
    # #     that we've used to obtain the new DNF stack and install it into the target userspace. Although
    # #     RHUI clients are being installed in both scratch and target containers, users can request their package
    # #     to be installed into target userspace that might add some repos to yum.repos.d that are not in scratch.

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


def _get_product_certificate_path():
    """
    Retrieve the required / used product certificate for RHSM.
    """
    architecture = api.current_actor().configuration.architecture
    target_version = api.current_actor().configuration.version.target
    target_product_type = get_product_type('target')
    certs_dir = api.get_common_folder_path(PROD_CERTS_FOLDER)

    # We do not need any special certificates to reach repos from non-ga channels, only beta requires special cert.
    if target_product_type != 'beta':
        target_product_type = 'ga'

    prod_certs = {
        'x86_64': {
            'ga': '479.pem',
            'beta': '486.pem',
        },
        'aarch64': {
            'ga': '419.pem',
            'beta': '363.pem',
        },
        'ppc64le': {
            'ga': '279.pem',
            'beta': '362.pem',
        },
        's390x': {
            'ga': '72.pem',
            'beta': '433.pem',
        }
    }

    try:
        cert = prod_certs[architecture][target_product_type]
    except KeyError as e:
        raise StopActorExecutionError(message='Failed to determine what certificate to use for {}.'.format(e))

    cert_path = os.path.join(certs_dir, target_version, cert)
    if not os.path.isfile(cert_path):
        additional_summary = ''
        if target_product_type != 'ga':
            additional_summary = (
                ' This can happen when upgrading a beta system and the chosen target version does not have'
                ' beta certificates attached (for example, because the GA has been released already).'

            )

        reporting.create_report([
            reporting.Title('Cannot find the product certificate file for the chosen target system.'),
            reporting.Summary(
                'Expected certificate: {cert} with path {path} but it could not be found.{additional}'.format(
                    cert=cert, path=cert_path, additional=additional_summary)
            ),
            reporting.Groups([reporting.Groups.REPOSITORY]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Remediation(hint=(
                'Set the corresponding target os version in the LEAPP_DEVEL_TARGET_RELEASE environment variable for'
                'which the {cert} certificate is provided'.format(cert=cert)
            )),
        ])
        raise StopActorExecution()

    return cert_path


def _create_target_userspace_directories(target_userspace):
    api.current_logger().debug('Creating target userspace directories.')
    try:
        utils.makedirs(target_userspace)
        api.current_logger().debug('Done creating target userspace directories.')
    except OSError:
        api.current_logger().error(
            'Failed to create temporary target userspace directories %s', target_userspace, exc_info=True)
        # This is an attempt for giving the user a chance to resolve it on their own
        raise StopActorExecutionError(
            message='Failed to prepare environment for package download while creating directories.',
            details={
                'hint': 'Please ensure that {directory} is empty and modifiable.'.format(directory=target_userspace)
            }
        )


def _inhibit_on_duplicate_repos(repofiles):
    """
    Inhibit the upgrade if any repoid is defined multiple times.

    When that happens, it not only shows misconfigured system, but then
    we can't get details of all the available repos as well.
    """
    # TODO: this is is duplicate of rhsm._inhibit_on_duplicate_repos
    # Issue: #486
    duplicates = repofileutils.get_duplicate_repositories(repofiles).keys()

    if not duplicates:
        return
    list_separator_fmt = '\n    - '
    api.current_logger().warning(
        'The following repoids are defined multiple times:{0}{1}'
        .format(list_separator_fmt, list_separator_fmt.join(duplicates))
    )

    reporting.create_report([
        reporting.Title('A YUM/DNF repository defined multiple times'),
        reporting.Summary(
            'The following repositories are defined multiple times inside the'
            ' "upgrade" container:{0}{1}'
            .format(list_separator_fmt, list_separator_fmt.join(duplicates))
        ),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.REPOSITORY]),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.Remediation(hint=(
            'Remove the duplicate repository definitions or change repoids of'
            ' conflicting repositories on the system to prevent the'
            ' conflict.'
            )
        )
    ])


def _get_all_available_repoids(context):
    repofiles = repofileutils.get_parsed_repofiles(context)
    # TODO: this is not good solution, but keep it as it is now
    # Issue: #486
    if rhsm.skip_rhsm():
        # only if rhsm is skipped, the duplicate repos are not detected
        # automatically and we need to do it extra
        _inhibit_on_duplicate_repos(repofiles)
    repoids = []
    for rfile in repofiles:
        if rfile.data:
            repoids += [repo.repoid for repo in rfile.data]
    return set(repoids)


def _get_rhsm_available_repoids(context):
    target_major_version = get_target_major_version()
    # FIXME: check that required repo IDs (baseos, appstream)
    # + or check that all required RHEL repo IDs are available.
    if rhsm.skip_rhsm():
        return set()
    # Get the RHSM repos available in the target RHEL container
    # TODO: very similar thing should happens for all other repofiles in container
    #
    repoids = rhsm.get_available_repo_ids(context)
    # NOTE(ivasilev) For the moment at least AppStream and BaseOS repos are required. While we are still
    # contemplating on what can be a generic solution to checking this, let's introduce a minimal check for
    # at-least-one-appstream and at-least-one-baseos among present repoids
    if not repoids or all("baseos" not in ri for ri in repoids) or all("appstream" not in ri for ri in repoids):
        reporting.create_report([
            reporting.Title('Cannot find required basic RHEL target repositories.'),
            reporting.Summary(
                'This can happen when a repository ID was entered incorrectly either while using the --enablerepo'
                ' option of leapp or in a third party actor that produces a CustomTargetRepositoryMessage.'
            ),
            reporting.Groups([reporting.Groups.REPOSITORY]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Remediation(hint=(
                'It is required to have RHEL repositories on the system'
                ' provided by the subscription-manager unless the --no-rhsm'
                ' option is specified. You might be missing a valid SKU for'
                ' the target system or have a failed network connection.'
                ' Check whether your system is attached to a valid SKU that is'
                ' providing RHEL {} repositories.'
                ' If you are using Red Hat Satellite, read the upgrade documentation'
                ' to set up Satellite and the system properly.'

            ).format(target_major_version)),
            reporting.ExternalLink(
                url='https://access.redhat.com/solutions/5392811',
                title='RHEL 7 to RHEL 8 LEAPP Upgrade Failing When Using Red Hat Satellite'
            ),
            reporting.ExternalLink(
                # https://red.ht/preparing-for-upgrade-to-rhel8
                # https://red.ht/preparing-for-upgrade-to-rhel9
                # https://red.ht/preparing-for-upgrade-to-rhel10
                url='https://red.ht/preparing-for-upgrade-to-rhel{}'.format(target_major_version),
                title='Preparing for the upgrade')
            ])
        raise StopActorExecution()
    return set(repoids)


def _get_rhui_available_repoids(context, cloud_repo):
    repofiles = repofileutils.get_parsed_repofiles(context)

    # TODO: same refactoring as Issue #486?
    _inhibit_on_duplicate_repos(repofiles)
    repoids = []
    for rfile in repofiles:
        if rfile.file == cloud_repo and rfile.data:
            repoids = [repo.repoid for repo in rfile.data]
            repoids.sort()
            break
    return set(repoids)


def get_copy_location_from_copy_in_task(context_basepath, copy_task):
    basename = os.path.basename(copy_task.src)
    dest_in_container = os.path.join(context_basepath, copy_task.dst)
    if os.path.isdir(dest_in_container):
        return os.path.join(copy_task.dst, basename)
    return copy_task.dst


def _get_rh_available_repoids(context, indata):
    """
    RH repositories are provided either by RHSM or are stored in the expected repo file provided by
    RHUI special packages (every cloud provider has itw own rpm).
    """

    rh_repoids = _get_rhsm_available_repoids(context)

    # If we are upgrading a RHUI system, check what repositories are provided by the (already installed) target clients
    if indata and indata.rhui_info:
        setup_info = indata.rhui_info.target_client_setup_info
        target_content_access_files = set()
        if setup_info.bootstrap_target_client:
            target_content_access_files = _query_rpm_for_pkg_files(context, indata.rhui_info.target_client_pkg_names)

        def is_repofile(path):
            return os.path.dirname(path) == '/etc/yum.repos.d' and os.path.basename(path).endswith('.repo')

        def extract_repoid_from_line(line):
            return line.split(':', 1)[1].strip()

        target_ver = api.current_actor().configuration.version.target
        setup_tasks = indata.rhui_info.target_client_setup_info.preinstall_tasks.files_to_copy_into_overlay

        yum_repos_d = context.full_path('/etc/yum.repos.d')
        all_repofiles = {os.path.join(yum_repos_d, path) for path in os.listdir(yum_repos_d) if path.endswith('.repo')}
        api.current_logger().debug('(RHUI Setup) All available repofiles: {0}'.format(' '.join(all_repofiles)))

        target_access_repofiles = {
            context.full_path(path) for path in target_content_access_files if is_repofile(path)
        }

        # Exclude repofiles used to setup the target rhui access as on some platforms the repos provided by
        # the client are not sufficient to install the client into target userspace (GCP)
        rhui_setup_repofile_tasks = [task for task in setup_tasks if task.src.endswith('repo')]
        rhui_setup_repofiles = (
            get_copy_location_from_copy_in_task(context.base_dir, copy) for copy in rhui_setup_repofile_tasks
        )
        rhui_setup_repofiles = {context.full_path(repofile) for repofile in rhui_setup_repofiles}

        foreign_repofiles = all_repofiles - target_access_repofiles - rhui_setup_repofiles

        api.current_logger().debug(
            'The following repofiles are considered as unknown to'
            ' the target RHUI content setup and will be ignored: {0}'.format(' '.join(foreign_repofiles))
        )

        # Rename non-client repofiles so they will not be recognized when running dnf repolist
        for foreign_repofile in foreign_repofiles:
            os.rename(foreign_repofile, '{0}.back'.format(foreign_repofile))

        try:
            dnf_cmd = ['dnf', 'repolist', '--releasever', target_ver, '-v', '--enablerepo', '*']
            repolist_result = context.call(dnf_cmd)['stdout']
            repoid_lines = [line for line in repolist_result.split('\n') if line.startswith('Repo-id')]
            rhui_repoids = {extract_repoid_from_line(line) for line in repoid_lines}
            rh_repoids.update(rhui_repoids)

        except CalledProcessError as err:
            details = {'err': err.stderr, 'details': str(err)}
            raise StopActorExecutionError(
                message='Failed to retrieve repoids provided by target RHUI clients.',
                details=details
            )

        finally:
            # Revert the renaming of non-client repofiles
            for foreign_repofile in foreign_repofiles:
                os.rename('{0}.back'.format(foreign_repofile), foreign_repofile)

    api.current_logger().debug(
        'The following repofiles are considered as provided by RedHat: {0}'.format(' '.join(rh_repoids))
    )
    return rh_repoids


def gather_target_repositories(context, indata):
    """
    Get available required target repositories and inhibit or raise error if basic checks do not pass.

    In case of repositories provided by Red Hat, it's checked whether the basic
    required repositories are available (or at least defined) in the given
    context. If not, raise StopActorExecutionError.

    For the custom target repositories we expect all of them have to be defined.
    If any custom target repository is missing, raise StopActorExecutionError.

    If any repository is defined multiple times, produce the inhibitor Report
    msg.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :return: List of target system repoids
    :rtype: List(string)
    """
    rh_available_repoids = _get_rh_available_repoids(context, indata)
    all_available_repoids = _get_all_available_repoids(context)

    target_repoids = []
    missing_custom_repoids = []
    for target_repo in api.consume(TargetRepositories):
        for rhel_repo in target_repo.rhel_repos:
            if rhel_repo.repoid in rh_available_repoids:
                target_repoids.append(rhel_repo.repoid)
            else:
                # TODO: We shall report that the RHEL repos that we deem necessary for
                # the upgrade are not available; but currently it would just print bunch of
                # data every time as we maps EUS and other repositories as well. But these
                # do not have to be necessary available on the target system in the time
                # of the upgrade. Let's skip it for now until it's clear how we will deal
                # with it.
                pass
        for custom_repo in target_repo.custom_repos:
            if custom_repo.repoid in all_available_repoids:
                target_repoids.append(custom_repo.repoid)
            else:
                missing_custom_repoids.append(custom_repo.repoid)
    api.current_logger().debug("Gathered target repositories: {}".format(', '.join(target_repoids)))
    if not target_repoids:
        target_major_version = get_target_major_version()
        reporting.create_report([
            reporting.Title('There are no enabled target repositories'),
            reporting.Summary(
                'This can happen when a system is not correctly registered with the subscription manager'
                ' or, when the leapp --no-rhsm option has been used, no custom repositories have been'
                ' passed on the command line.'
            ),
            reporting.Groups([reporting.Groups.REPOSITORY]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Remediation(hint=(
                'Ensure the system is correctly registered with the subscription manager and that'
                ' the current subscription is entitled to install the requested target version {version}.'
                ' If you used the --no-rhsm option (or the LEAPP_NO_RHSM=1 environment variable is set),'
                ' ensure the custom repository file is provided with'
                ' properly defined repositories and that the --enablerepo option for leapp is set if the'
                ' repositories are defined in any repofiles under the /etc/yum.repos.d/ directory.'
                ' For more information on custom repository files, see the documentation.'
                ' Finally, verify that the "/etc/leapp/files/repomap.json" file is up-to-date.'
            ).format(version=api.current_actor().configuration.version.target)),
            reporting.ExternalLink(
                # https://red.ht/preparing-for-upgrade-to-rhel8
                # https://red.ht/preparing-for-upgrade-to-rhel9
                # https://red.ht/preparing-for-upgrade-to-rhel10
                url='https://red.ht/preparing-for-upgrade-to-rhel{}'.format(target_major_version),
                title='Preparing for the upgrade'),
            reporting.ExternalLink(
                url='https://access.redhat.com/solutions/7001181',
                title='LEAPP Upgrade Failing from RHEL 7 to RHEL 8 when system is '
                      'registered to custromer portal'
            ),
            reporting.RelatedResource("file", "/etc/leapp/files/repomap.json"),
            reporting.RelatedResource("file", "/etc/yum.repos.d/")
        ])
        raise StopActorExecution()
    if missing_custom_repoids:
        reporting.create_report([
            reporting.Title('Some required custom target repositories have not been found'),
            reporting.Summary(
                'This can happen when a repository ID was entered incorrectly either'
                ' while using the --enablerepo option of leapp, or in a third party actor that produces a'
                ' CustomTargetRepositoryMessage.\n'
                'The following repositories IDs could not be found in the target configuration:\n'
                '- {}\n'.format('\n- '.join(missing_custom_repoids))
            ),
            reporting.Groups([reporting.Groups.REPOSITORY]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.ExternalLink(
                # NOTE: Article covers both RHEL 7 to RHEL 8 and RHEL 8 to RHEL 9
                url='https://access.redhat.com/articles/4977891',
                title='Customizing your Red Hat Enterprise Linux in-place upgrade'),
            reporting.Remediation(hint=(
                'Consider using the custom repository file, which is documented in the official'
                ' upgrade documentation. Check whether a repository ID has been'
                ' entered incorrectly with the --enablerepo option of leapp.'
                ' Check the leapp logs to see the list of all available repositories.'
            ))
        ])
        raise StopActorExecution()
    return set(target_repoids)


def _install_custom_repofiles(context, custom_repofiles):
    """
    Install the required custom repository files into the container.

    The repository files are copied from the host into the /etc/yum.repos.d
    directory into the container.

    :param context: the container where the repofiles should be copied
    :type context: mounting.IsolatedActions class
    :param custom_repofiles: list of custom repo files
    :type custom_repofiles: List(CustomTargetRepositoryFile)
    """
    for rfile in custom_repofiles:
        _dst_path = os.path.join('/etc/yum.repos.d', os.path.basename(rfile.file))
        context.copy_to(rfile.file, _dst_path)


def _gather_target_repositories(context, indata, prod_cert_path):
    """
    This is wrapper function to gather the target repoids.

    Probably the function could be partially merged into gather_target_repositories
    and this could be really just wrapper with the switch of certificates.
    I am keeping that for now as it is as interim step.

    :param context: the container where the repofiles should be copied
    :type context: mounting.IsolatedActions class
    :param indata: majority of input data for the actor
    :type indata: class _InputData
    :param prod_cert_path: path where the target product cert is stored
    :type prod_cert_path: string
    """
    rhsm.set_container_mode(context)
    rhsm.switch_certificate(context, indata.rhsm_info, prod_cert_path)

    _install_custom_repofiles(context, indata.custom_repofiles)
    return gather_target_repositories(context, indata)


def _copy_files(context, files):
    """
    Copy the files/dirs from the host to the `context` userspace

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :param files: list of files that should be copied from the host to the context
    :type files: list of CopyFile
    """
    for file_task in files:
        if not file_task.dst:
            file_task.dst = file_task.src
        if os.path.isdir(file_task.src):
            context.remove_tree(file_task.dst)
            context.copytree_to(file_task.src, file_task.dst)
        else:
            context.copy_to(file_task.src, file_task.dst)


def _get_target_userspace():
    return constants.TARGET_USERSPACE.format(get_target_major_version())


def _create_target_userspace(context, indata, packages, files, target_repoids):
    """Create the target userspace."""
    target_path = _get_target_userspace()
    prepare_target_userspace(context, target_path, target_repoids, list(packages))
    _prep_repository_access(context, target_path)

    with mounting.NspawnActions(base_dir=target_path) as target_context:
        _copy_files(target_context, files)
    dnfplugin.install(_get_target_userspace())

    # If we used only repofiles from leapp-rhui-<provider> then remove these as they provide
    # duplicit definitions as the target clients already installed in the target container
    if indata.rhui_info:
        api.current_logger().debug(
            'Target container should have access to content. '
            'Removing repofiles from leapp-rhui-<provider> from the target..'
        )
        setup_info = indata.rhui_info.target_client_setup_info
        if not setup_info.bootstrap_target_client:
            target_userspace_path = _get_target_userspace()
            for copy in setup_info.preinstall_tasks.files_to_copy_into_overlay:
                dst_in_container = get_copy_location_from_copy_in_task(target_userspace_path, copy)
                dst_in_container = dst_in_container.strip('/')
                dst_in_host = os.path.join(target_userspace_path, dst_in_container)
                if os.path.isfile(dst_in_host) and dst_in_host.endswith('.repo'):
                    api.current_logger().debug('Removing repofile: {0}'.format(dst_in_host))
                    os.remove(dst_in_host)

    # and do not forget to set the rhsm into the container mode again
    with mounting.NspawnActions(_get_target_userspace()) as target_context:
        rhsm.set_container_mode(target_context)


def _apply_rhui_access_preinstall_tasks(context, rhui_setup_info):
    if rhui_setup_info.preinstall_tasks:
        api.current_logger().debug('Applying RHUI preinstall tasks.')
        preinstall_tasks = rhui_setup_info.preinstall_tasks

        for file_to_remove in preinstall_tasks.files_to_remove:
            api.current_logger().debug('Removing {0} from the scratch container.'.format(file_to_remove))
            context.remove(file_to_remove)

        for copy_info in preinstall_tasks.files_to_copy_into_overlay:
            api.current_logger().debug(
                'Copying {0} in {1} into the scratch container.'.format(copy_info.src, copy_info.dst)
            )
            context.makedirs(os.path.dirname(copy_info.dst), exists_ok=True)
            context.copy_to(copy_info.src, copy_info.dst)


def _apply_rhui_access_postinstall_tasks(context, rhui_setup_info):
    if rhui_setup_info.postinstall_tasks:
        api.current_logger().debug('Applying RHUI postinstall tasks.')
        for copy_info in rhui_setup_info.postinstall_tasks.files_to_copy:
            context.makedirs(os.path.dirname(copy_info.dst), exists_ok=True)
            debug_msg = 'Copying {0} to {1} (inside the scratch container).'
            api.current_logger().debug(debug_msg.format(copy_info.src, copy_info.dst))
            context.call(['cp', copy_info.src, copy_info.dst])


def setup_target_rhui_access_if_needed(context, indata):
    if not indata.rhui_info:
        return

    target_major_version = get_target_major_version()
    userspace_dir = _get_target_userspace()
    _create_target_userspace_directories(userspace_dir)

    setup_info = indata.rhui_info.target_client_setup_info
    _apply_rhui_access_preinstall_tasks(context, setup_info)

    if not setup_info.bootstrap_target_client:
        # Installation of the target RHUI client is not possible and we bundle all necessary
        # files into the leapp-rhui-<provider> packages.
        api.current_logger().debug('Bootstrapping target RHUI client is disabled, leapp will rely '
                                   'only on files budled in leapp-rhui-<provider> package.')
        return

    cmd = ['dnf', '-y']

    if setup_info.enable_only_repoids_in_copied_files and setup_info.preinstall_tasks:
        copy_tasks = setup_info.preinstall_tasks.files_to_copy_into_overlay
        copied_repofiles = [copy.src for copy in copy_tasks if copy.src.endswith('.repo')]
        copied_repoids = set()
        for repofile in copied_repofiles:
            repofile_contents = repofileutils.parse_repofile(repofile)
            copied_repoids.update(entry.repoid for entry in repofile_contents.data)

        cmd += ['--disablerepo', '*']
        for copied_repoid in copied_repoids:
            cmd.extend(('--enablerepo', copied_repoid))

    src_client_remove_steps = ['remove {0}'.format(client) for client in indata.rhui_info.src_client_pkg_names]
    target_client_install_steps = ['install {0}'.format(client) for client in indata.rhui_info.target_client_pkg_names]

    dnf_transaction_steps = src_client_remove_steps + target_client_install_steps + ['transaction run']

    cmd += [
        '--setopt=module_platform_id=platform:el{}'.format(target_major_version),
        '--setopt=keepcache=1',
        '--releasever', api.current_actor().configuration.version.target,
        '--disableplugin', 'subscription-manager',
        'shell'
    ]

    context.call(cmd, callback_raw=utils.logging_handler, stdin='\n'.join(dnf_transaction_steps))

    _apply_rhui_access_postinstall_tasks(context, setup_info)

    # Do a cleanup so there are not duplicit repoids
    try:
        files_owned_by_clients = _query_rpm_for_pkg_files(context, indata.rhui_info.target_client_pkg_names)
    except CalledProcessError as err:  # We failed to rpm -qf PKG, the PKG is most likely not installed
        api.current_logger().critical('Failed to query files owned by target RHUI clients (clients=%s). This is caused'
                                      ' by failing to install the target clients during the client-swap step.'
                                      ' Full error: %s', indata.rhui_info.target_client_pkg_names, err)

        target_major = get_target_major_version()
        plural_suffix = 's' if len(indata.rhui_info.target_client_pkg_names) > 1 else ''
        client_rpms = ', '.join(indata.rhui_info.target_client_pkg_names)
        msg = ('Could not find the RHEL {target_major} RHUI client rpm{plural_suffix} ({client_rpms})'
               ' in the cloud provider\'s client repository.')
        raise StopActorExecutionError(msg.format(target_major=target_major, plural_suffix=plural_suffix,
                                                 client_rpms=client_rpms))

    for copy_task in setup_info.preinstall_tasks.files_to_copy_into_overlay:
        dest = get_copy_location_from_copy_in_task(context.base_dir, copy_task)
        can_be_cleaned_up = copy_task.src not in setup_info.files_supporting_client_operation
        if dest not in files_owned_by_clients and can_be_cleaned_up:
            context.remove(dest)


@suppress_deprecation(TMPTargetRepositoriesFacts)
def perform():
    # NOTE: this one action is out of unit-tests completely; we do not use
    # in unit tests the LEAPP_DEVEL_SKIP_RHSM envar anymore
    _check_deprecated_rhsm_skip()

    indata = _InputData()
    prod_cert_path = _get_product_certificate_path()
    reserve_space = overlaygen.get_recommended_leapp_free_space(_get_target_userspace())
    with overlaygen.create_source_overlay(
            mounts_dir=constants.MOUNTS_DIR,
            scratch_dir=constants.SCRATCH_DIR,
            storage_info=indata.storage_info,
            xfs_info=indata.xfs_info,
            scratch_reserve=reserve_space) as overlay:
        with overlay.nspawn() as context:
            # Mount the ISO into the scratch container
            target_iso = next(api.consume(TargetOSInstallationImage), None)
            with mounting.mount_upgrade_iso_to_root_dir(overlay.target, target_iso):

                setup_target_rhui_access_if_needed(context, indata)

                target_repoids = _gather_target_repositories(context, indata, prod_cert_path)
                _create_target_userspace(context, indata, indata.packages, indata.files, target_repoids)
                # TODO: this is tmp solution as proper one needs significant refactoring
                target_repo_facts = repofileutils.get_parsed_repofiles(context)
                api.produce(TMPTargetRepositoriesFacts(repositories=target_repo_facts))
                # ## TODO ends here
                api.produce(UsedTargetRepositories(
                    repos=[UsedTargetRepository(repoid=repo) for repo in target_repoids]))
                api.produce(TargetUserSpaceInfo(
                    path=_get_target_userspace(),
                    scratch=constants.SCRATCH_DIR,
                    mounts=constants.MOUNTS_DIR))
