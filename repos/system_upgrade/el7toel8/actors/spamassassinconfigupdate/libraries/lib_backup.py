import errno
import os
import shutil
import tempfile


def backup_file(path):
    """ Backup the file specified by path and return the path to the backup file. """
    backup_path = '%s.leapp-backup' % path
    try:
        fd = os.open(backup_path, os.O_CREAT | os.O_EXCL, 0o600)
    except OSError as e:
        if e.errno == errno.EEXIST:
            file_name = os.path.basename(backup_path)
            fd, backup_path = tempfile.mkstemp(prefix=file_name + '.',
                                               dir=os.path.dirname(backup_path))
        else:
            raise
    os.close(fd)

    shutil.copyfile(path, backup_path)
    return backup_path
