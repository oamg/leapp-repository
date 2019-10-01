import os
import shutil
import stat

UMASK = 0o600


class NotNSSConfiguration(RuntimeError):
    pass


class AlreadyConverted(RuntimeError):
    pass


class InsufficientTooling(RuntimeError):
    pass


def copy_permissions(orig, new):
    """Copy permissions, owner and group to the another file."""
    try:
        try:
            shutil.copymode(orig, new)
        except BaseException as e:
            raise RuntimeError('Could not copy mode of `%s` to `%s`, the error was: %s' % (orig, new, e))

        try:
            st = os.stat(orig)
        except BaseException as e:
            raise RuntimeError('Could not stat `%s`, the error was: %s' % (orig, e))

        try:
            os.chown(new, st[stat.ST_UID], st[stat.ST_GID])
        except BaseException as e:
            raise RuntimeError('Could not change owner of `%s`, the error was: %s' % (new, e))
    except RuntimeError as e:
        raise RuntimeError('Could not copy metadata from `%s` to `%s`, the error was: %s' % (orig, new, e))


def copy_some_permissions(filename, interpolations, dest):
    for i in interpolations:
        fn = filename % i
        try:
            os.stat(fn)
        except IOError:
            pass  # file does not exist, try another one
        copy_permissions(fn, dest)
        return True
    raise RuntimeError('Could not set properties of `%s`' % dest)
