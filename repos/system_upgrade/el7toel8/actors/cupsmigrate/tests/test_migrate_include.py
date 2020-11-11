import pytest

from leapp.libraries.actor.cupsmigrate import migrate_include


class MockFileSystem(object):
    def __init__(self,
                 infiles):
        self.files = {}
        self.ssl_dir = []
        self.files = infiles
        for path in infiles.keys():
            if path.startswith('ssl') or path.startswith('/etc/cups/ssl'):
                self.ssl_dir.append(path.rsplit('/', 1)[1])

    def readlines(self, path):
        if path in self.files.keys():
            return self.files[path].splitlines(True)
        raise IOError('Error when reading file {} - file '
                      'does not exist.'.format(path))

    def write(self, path, mode, content):
        if isinstance(content, list):
            content = ''.join(content)

        if mode == 'w':
            self.files[path] = content
        else:
            self.files[path] += content

    def copy_to_ssl(self, oldpath):
        self.ssl_dir.append(oldpath.rsplit('/', 1)[1])


testdata = (
    (
        {
            '/etc/cups/cupsd.conf': 'ifdfdfgfg\n'
        },
        ['/etc/cups/cupsd.conf'],
        'ifdfdfgfg\n'
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'Include smth.conf\nHello world\n',
            'smth.conf': 'Policy two\n'
        },
        ['/etc/cups/cupsd.conf', 'smth.conf'],
        'Hello world\n\n# added by Leapp\nPolicy two\n'
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'Include smth.conf\nHello world\n',
            'smth.conf': 'Include any.conf\nMake my day\n',
            'any.conf': 'Go ahead\n'
        },
        ['/etc/cups/cupsd.conf', 'smth.conf', 'any.conf'],
        'Hello world\n\n# added by Leapp\nMake my day\n\n# added by Leapp\nGo ahead\n'
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'Include smth.conf\nHello world\n',
            'smth.conf': '#Include any.conf\nMake my day\n',
            'any.conf': 'Go ahead\n'
        },
        ['/etc/cups/cupsd.conf', 'smth.conf'],
        'Hello world\n\n# added by Leapp\n#Include any.conf\nMake my day\n'
    )
)


@pytest.mark.parametrize('files,included_files,expected', testdata)
def test_migrate_include(files, included_files, expected):
    op = MockFileSystem(infiles=files)

    migrate_include(included_files, op)

    assert op.files.get('/etc/cups/cupsd.conf', None) == expected
