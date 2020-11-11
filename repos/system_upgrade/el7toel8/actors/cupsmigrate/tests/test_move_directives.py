import pytest

from leapp.libraries.actor.cupsmigrate import move_directives


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
            '/etc/cups/cupsd.conf': 'ifdfdfgfg\n',
            '/etc/cups/cups-files.conf': 'clean\n'
        },
        {
            '/etc/cups/cupsd.conf': 'ifdfdfgfg\n',
            '/etc/cups/cups-files.conf': 'clean\n'
        }
    ),
    (
        {
            '/etc/cups/cupsd.conf': '#PassEnv smht\nHello world\n',
            '/etc/cups/cups-files.conf': 'clean\n'
        },
        {
            '/etc/cups/cupsd.conf': '#PassEnv smht\nHello world\n',
            '/etc/cups/cups-files.conf': 'clean\n'
        }
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'PassEnv smth\nHello world\n',
            '/etc/cups/cups-files.conf': 'clean\n'
        },
        {
            '/etc/cups/cupsd.conf': 'Hello world\n',
            '/etc/cups/cups-files.conf': 'clean\n\n# added by Leapp\nPassEnv smth\n'
        }
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'SetEnv smht to\nHello world\n',
            '/etc/cups/cups-files.conf': 'clean\n'
        },
        {
            '/etc/cups/cupsd.conf': 'Hello world\n',
            '/etc/cups/cups-files.conf': 'clean\n\n# added by Leapp\nSetEnv smht to\n'
        }
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'PassEnv smht\nSetEnv set to\nHello world\n',
            '/etc/cups/cups-files.conf': 'clean\n'
        },
        {
            '/etc/cups/cupsd.conf': 'Hello world\n',
            '/etc/cups/cups-files.conf': 'clean\n\n# added by Leapp\n'
                                         'PassEnv smht\nSetEnv set to\n'
        }
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'PassEnv smth\nSetEnv set to\nPri'
                                    'ntcapFormat any\nHello world\n',
            '/etc/cups/cups-files.conf': 'clean\n'
        },
        {
            '/etc/cups/cupsd.conf': 'Hello world\n',
            '/etc/cups/cups-files.conf': 'clean\n\n# added by Leapp\n'
                                         'PassEnv smth\nSetEnv set to'
                                         '\nPrintcapFormat any\n'
        }
    )
)


@pytest.mark.parametrize('files,expected', testdata)
def test_move_directives(files, expected):
    op = MockFileSystem(infiles=files)

    move_directives(['PassEnv', 'SetEnv', 'PrintcapFormat'], op)

    assert op.files.get('/etc/cups/cupsd.conf', None) == expected.get('/etc/cups/cupsd.conf', None)
    assert op.files.get('/etc/cups/cups-files.conf', None) == expected.get('/etc/cups/cups-files.conf', None)
