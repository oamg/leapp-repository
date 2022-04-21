import os
import shutil

from leapp.libraries.stdlib import api, CalledProcessError, run

# dict(orig_dir: new_dir)
DIRS_CHANGE = {
    '/etc/pki/ca-trust/source/blacklist/': '/etc/pki/ca-trust/source/blocklist/',
    '/usr/share/pki/ca-trust-source/blacklist/': '/usr/share/pki/ca-trust-source/blocklist/'
}


def _link_src_path(filepath):
    """
    Return expected target path for the symlink.

    In case the symlink points to one of dirs supposed to be migrated in this
    actor, we need to point to the new directory instead.

    In case the link points anywhere else, keep the target path as it is.
    """
    realpath = os.path.realpath(filepath)
    for dirname in DIRS_CHANGE:
        if realpath.startswith(dirname):
            return realpath.replace(dirname, DIRS_CHANGE[dirname])

    # it seems we can keep this path
    return realpath


def _migrate_file(filename, src_basedir):
    dst_path = filename.replace(src_basedir, DIRS_CHANGE[src_basedir])
    if os.path.exists(dst_path):
        api.current_logger().info(
            'Skipping migration of the {} certificate. The target file already exists'
            .format(filename)
        )
        return
    os.makedirs(os.path.dirname(dst_path), mode=0o755, exist_ok=True)
    if os.path.islink(filename):
        # create the new symlink instead of the moving the file
        # as the target path could be different as well
        link_src_path = _link_src_path(filename)
        # TODO: is the broken symlink ok?
        os.symlink(link_src_path, dst_path)
        os.unlink(filename)
    else:
        # normal file, just move it
        shutil.move(filename, dst_path)


def _get_files(dirname):
    return run(['find', dirname, '-type', 'f,l'], split=True)['stdout']


def process():
    for dirname in DIRS_CHANGE:
        if not os.path.exists(dirname):
            # The directory does not exist; nothing to do here
            continue
        try:
            blacklisted_certs = _get_files(dirname)
        except (CalledProcessError, OSError) as e:
            # TODO: create post-upgrade report
            api.current_logger().error('Cannot get list of files in {}: {}.'.format(dirname, e))
            api.current_logger().error('Certificates under {} must be migrated manually.'.format(dirname))
            continue
        failed_files = []
        for filename in blacklisted_certs:
            try:
                _migrate_file(filename, dirname)
            except OSError as e:
                api.current_logger().error(
                    'Failed migration of blacklisted certificate {}: {}'
                    .format(filename, e)
                )
                failed_files.append(filename)
        if not failed_files:
            # the failed removal is not such a big issue here
            # clean the dir if all files have been migrated successfully
            shutil.rmtree(dirname, ignore_errors=True)
    try:
        run(['/usr/bin/update-ca-trust'])
    except (CalledProcessError, OSError) as e:
        api.current_logger().error(
            'Cannot update CA trust on the system.'
            ' It needs to be done manually after the in-place upgrade.'
            ' Reason: {}'.format(e)
        )
