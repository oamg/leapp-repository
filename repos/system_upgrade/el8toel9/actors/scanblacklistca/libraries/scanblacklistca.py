import os

from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import BlackListCA, BlackListError

# dict(orig_dir: new_dir)
DIRS_CHANGE = {
    '/etc/pki/ca-trust/source/blacklist/': '/etc/pki/ca-trust/source/blocklist/',
    '/usr/share/pki/ca-trust-source/blacklist/': '/usr/share/pki/ca-trust-source/blocklist/'
}


def _get_dirs():
    return DIRS_CHANGE


def _get_files(dirname):
    """
    :raises: CalledProcessError: if the find command fails
    """
    # on rhel8, -type can't take two arguments, so we need to call find
    # twice and concatenate the results
    files = run(['find', dirname, '-type', 'f'], split=True)['stdout']
    return files + run(['find', dirname, '-type', 'l'], split=True)['stdout']


def _generate_messages(dirname, targetname):
    if not os.path.exists(dirname):
        # The directory does not exist; not an error (there is just nothing
        # to migrate).
        return
    try:
        blacklisted_certs = _get_files(dirname)
    except (CalledProcessError) as e:
        api.produce(BlackListError(sourceDir=dirname, targetDir=targetname, error=str(e)))
        api.current_logger().error('Cannot get list of files in {}: {}.'.format(dirname, e))
        return
    for filename in blacklisted_certs:
        # files found, pass a message to the reporter.
        # (maybe to migrateblacklistca as well)
        target = filename.replace(dirname, targetname)
        api.produce(BlackListCA(source=filename, sourceDir=dirname, target=target, targetDir=targetname))


def process():
    change_dirs = _get_dirs()
    for dirname in change_dirs:
        _generate_messages(dirname, change_dirs[dirname])
