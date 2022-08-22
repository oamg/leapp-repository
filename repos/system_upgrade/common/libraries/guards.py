import contextlib
import os

from six.moves.urllib.error import URLError
from six.moves.urllib.request import urlopen

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import CalledProcessError


@contextlib.contextmanager
def guarded_execution(*guards):
    try:
        yield
    except CalledProcessError as e:
        # collect output from guards for possible spurious failure
        guard_errors = []
        for guard in guards:
            err = guard()
            if err:
                guard_errors.append(err)

        details = None
        if guard_errors:
            details = {
                'hint': 'Possible spurious failure: {cause}'.format(cause=' '.join(guard_errors))
            }
        raise StopActorExecutionError(
            message=str(e),
            details=details
        )


def connection_guard(url='https://example.com'):
    def closure():
        try:
            urlopen(url)
            return None
        except URLError as e:
            cause = '''Failed to open url '{url}' with error: {error}'''.format(url=url, error=e)
            return ('There was probably a problem with internet conection ({cause}).'
                    ' Check your connection and try again.'.format(cause=cause))
    return closure


def space_guard(path='/', min_free_mb=100):
    def closure():
        info = os.statvfs(path)
        free_mb = (info.f_bavail * info.f_frsize) >> 20
        if free_mb >= min_free_mb:
            return None
        return ('''Not enough free disk space in '{path}', needed: {min} M, available: {avail} M.'''
                ' Free more disk space and try again.'.format(path=path, min=min_free_mb, avail=free_mb))
    return closure
