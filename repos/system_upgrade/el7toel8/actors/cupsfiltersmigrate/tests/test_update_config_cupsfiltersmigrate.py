import pytest

from leapp.libraries.actor.cupsfiltersmigrate import NEW_MACROS, update_config


def _gen_append_str(list_out=None):
    """
    Just helper function to generate string expected to be added for an input (see testdata) for testing.

    :param list list_out: None, [0], [1], [0,1] - no more expected vals,
                          which represents what macros should be appended
                          in output
    """
    if not list_out:
        return ''
    _out_list = ('LocalQueueNamingRemoteCUPS RemoteName', 'CreateIPPPrinterQueues All')
    output = ['# content added by Leapp']
    for i in list_out:
        output.append(_out_list[i])
    # ensure the extra NL is before the string and the empty NL is in the end
    # of the string (/file) as well
    return '\n{}\n'.format('\n'.join(output))


testdata = (
    ('\n',
        _gen_append_str([0, 1])),
    ('bleblaba\n',
        _gen_append_str([0, 1])),
    ('fdnfdf\n# LocalQueueNamingRemoteCUPS RemoteName\n',
        _gen_append_str([0, 1])),
    ('fdnfdf\nfoo # LocalQueueNamingRemoteCUPS RemoteName\n',
        _gen_append_str([0, 1])),
    ('fdnfdf\n# LocalQueueNamingRemoteCUPS Bar\n',
        _gen_append_str([0, 1])),
    ('fdnfdf\n  # LocalQueueNamingRemoteCUPS Bar\n',
        _gen_append_str([0, 1])),
    ('fdnfdf\nLocalQueueNamingRemoteCUPS RemoteName\n',
        _gen_append_str([1])),
    ('fdnfdf\n  LocalQueueNamingRemoteCUPS RemoteName\n',
        _gen_append_str([1])),
    ('fdnfdf\nLocalQueueNamingRemoteCUPS Bar\n',
        _gen_append_str([1])),
    ('fnfngbfg\nCreateIPPPrinterQueues All\n',
        _gen_append_str([0])),
    ('fnfngbfg\nCreateIPPPrinterQueues Foo\n',
        _gen_append_str([0])),
    ('fnfngbfg\n  CreateIPPPrinterQueues Foo\n',
        _gen_append_str([0])),
    ('CreateIPPPrinterQueues All\nLocalQueueNamingRemoteCUPS RemoteName\n',
        _gen_append_str()),
    ('CreateIPPPrinterQueues Foo\nLocalQueueNamingRemoteCUPS Bar\n',
        _gen_append_str()),
    ('foo\nCreateIPPPrinterQueues Foo\nLocalQueueNamingRemoteCUPS Bar\nFoobar\n',
        _gen_append_str()),
    ('foo\nCreateIPPPrinterQueues Foo\n# LocalQueueNamingRemoteCUPS Bar\nFoobar\n',
        _gen_append_str([0]))
)


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

    def exists(self, path, macro):
        for line in self.content.split('\n'):
            if line.lstrip().startswith(macro) and self.path == path:
                return True
        return False


def test_update_config_file_errors():
    path = 'foo'

    f = MockFile(path, content='')

    with pytest.raises(IOError):
        update_config('bar', f.exists, f.append)

    assert f.content == ''


@pytest.mark.parametrize('content,expected', testdata)
def test_update_config_append_into_file(content, expected):
    path = 'bar'
    f = MockFile(path, content)

    update_config(path, f.exists, f.append)

    assert f.content == content + expected
