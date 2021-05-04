import errno

from leapp.libraries.common.testutils import make_IOError, make_OSError


def test_make_IOError():
    exception = make_IOError(errno.ENOENT)
    assert isinstance(exception, IOError)
    assert exception.errno == errno.ENOENT

    exception = make_IOError(errno.ENOTDIR)
    assert isinstance(exception, IOError)
    assert exception.errno == errno.ENOTDIR


def test_make_OSError():
    exception = make_OSError(errno.ENOENT)
    assert isinstance(exception, OSError)
    assert exception.errno == errno.ENOENT

    exception = make_OSError(errno.ENOTDIR)
    assert isinstance(exception, OSError)
    assert exception.errno == errno.ENOTDIR
