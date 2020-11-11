import pytest

from leapp.libraries.actor.cupsmigrate import migrate_digest


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
        'ifdfdfgfg\n'
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'AuthType Basic\nHello world\n',
        },
        'AuthType Basic\nHello world\n'
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'DefaultAuthType Negotiate\nHello world\n',
        },
        'DefaultAuthType Negotiate\nHello world\n'
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'AuthType Digest\nHello world\n',
        },
        'AuthType Basic\nHello world\n'
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'DefaultAuthType Digest\nHello world\n',
        },
        'DefaultAuthType Basic\nHello world\n'
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'DefaultAuthType BasicDigest\nHello world\n',
        },
        'DefaultAuthType Basic\nHello world\n'
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'AuthType BasicDigest\nHello world\n',
        },
        'AuthType Basic\nHello world\n'
    ),
    (
        {
            '/etc/cups/cupsd.conf': '#AuthType BasicDigest\nHello world\n',
        },
        '#AuthType BasicDigest\nHello world\n'
    )
)


@pytest.mark.parametrize('files,expected', testdata)
def test_migrate_digest(files, expected):
    op = MockFileSystem(infiles=files)

    migrate_digest(op)

    assert op.files.get('/etc/cups/cupsd.conf', None) == expected
