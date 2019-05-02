import errno

from leapp.libraries.common.testutils import make_IOError
from leapp.libraries.common.vsftpdutils import get_config_contents, get_default_config_hash


class MockFile(object):
    def __init__(self, path, content=None, to_raise=None):
        self.path = path
        self.content = content
        self.to_raise = to_raise
        self.error = False

    def read_file(self, path):
        if path != self.path:
            self.error = True
            raise ValueError
        if not self.to_raise:
            return self.content
        raise self.to_raise


def test_getting_nonexistent_config_gives_None():
    path = 'my_file'
    f = MockFile(path, to_raise=make_IOError(errno.ENOENT))

    res = get_config_contents(path, read_func=f.read_file)

    assert not f.error
    assert res is None


def test_getting_inaccessible_config_gives_None():
    path = 'my_file'
    f = MockFile(path, to_raise=make_IOError(errno.EACCES))

    res = get_config_contents(path, read_func=f.read_file)

    assert not f.error
    assert res is None


def test_getting_empty_config_gives_empty_string():
    path = 'my_file'
    f = MockFile(path, content='')

    res = get_config_contents(path, read_func=f.read_file)

    assert not f.error
    assert res == ''


def test_getting_nonempty_config_gives_the_content():
    path = 'my_file'
    content = 'foo\nbar\n'
    f = MockFile(path, content=content)

    res = get_config_contents(path, read_func=f.read_file)

    assert not f.error
    assert res == content


def test_hash_of_default_config_is_correct():
    path = '/etc/vsftpd/vsftpd.conf'
    content = 'foo\n'
    f = MockFile(path, content=content)

    h = get_default_config_hash(read_func=f.read_file)

    assert h == 'f1d2d2f924e986ac86fdf7b36c94bcdf32beec15'
    assert not f.error


def test_hash_of_nonexistent_default_config_is_None():
    path = '/etc/vsftpd/vsftpd.conf'
    f = MockFile(path, to_raise=make_IOError(errno.ENOENT))

    h = get_default_config_hash(read_func=f.read_file)

    assert h is None
    assert not f.error
