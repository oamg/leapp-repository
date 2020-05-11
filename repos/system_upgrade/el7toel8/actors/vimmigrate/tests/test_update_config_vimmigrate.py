import pytest

from leapp.libraries.actor.vimmigrate import new_macros, update_config


class MockFile(object):
    def __init__(self, path, content=None):
        self.path = path
        self.content = content
        self.error = False

    def append(self, path, content):
        if path != self.path:
            self.error = True
        if not self.error:
            self.content += content
            return self.content
        raise IOError('Error during writing to file: {}.'.format(path))


def test_update_config_file_errors(path='foo'):
    f = MockFile(path, content='')

    with pytest.raises(IOError):
        update_config('bar', f.append)

    assert f.content == ''


@pytest.mark.parametrize('content', ('', 'bleblaba'))
def test_update_config_append_into_file(content):
    path = 'bar'

    fmt_input = "\n{comment_line}\n{content}\n".format(comment_line='" content added by Leapp',
                                                       content='\n'.join(new_macros))

    f = MockFile(path, content)
    res = update_config(path, f.append)

    assert res is None
    assert f.content == content + fmt_input
