import pytest

from leapp.libraries.actor.cupsmigrate import migrate_certkey


class MockFileSystem(object):
    def __init__(self,
                 infiles):
        self.files = {}
        self.ssl_dir = []
        self.files = infiles
        for path in infiles.keys():
            if path.startswith('/etc/cups/ssl'):
                self.ssl_dir.append(path)

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
        self.ssl_dir.append('/etc/cups/ssl/' + oldpath.rsplit('/', 1)[1])


testdata = (
    (
        {
            '/etc/cups/cups-files.conf': 'ifdfdfgfg\n'
        },
        {
            '/etc/cups/cups-files.conf': 'ifdfdfgfg\n'
        }
    ),
    (
        {
            '/etc/cups/cups-files.conf': 'ServerKey /etc/cups/ssl/ser'
                                         'ver.key\nHello world\n',
            '/etc/cups/ssl/server.key': ''
        },
        {
            '/etc/cups/cups-files.conf': 'Hello world\n',
            'ssl-dir': ['/etc/cups/ssl/server.key']
        }
    ),
    (
        {
            '/etc/cups/cups-files.conf': '#ServerKey /etc/cups/ssl/se'
                                         'rver.key\nHello world\n',
            '/etc/cups/ssl/server.key': ''
        },
        {
            '/etc/cups/cups-files.conf': '#ServerKey /etc/cups/ssl/se'
                                         'rver.key\nHello world\n',
            'ssl-dir': ['/etc/cups/ssl/server.key']
        }
    ),
    (
        {
            '/etc/cups/cups-files.conf': 'ServerCertificate /etc/cups'
                                         '/ssl/server.cert\nHello world\n',
            '/etc/cups/ssl/server.cert': ''
        },
        {
            '/etc/cups/cups-files.conf': 'Hello world\n',
            'ssl-dir': ['/etc/cups/ssl/server.cert']
        }
    ),
    (
        {
            '/etc/cups/cups-files.conf': 'ServerCertificate /etc/cups'
                                         '/ssl/server.cert\nServerKey'
                                         ' /etc/cups/ssl/server.key\n'
                                         'Hello world\n',
            '/etc/cups/ssl/server.cert': '',
            '/etc/cups/ssl/server.key': ''
        },
        {
            '/etc/cups/cups-files.conf': 'Hello world\n',
            'ssl-dir': ['/etc/cups/ssl/server.cert',
                        '/etc/cups/ssl/server.key']
        }
    ),
    (
        {
            '/etc/cups/cups-files.conf': 'ServerCertificate ssl/serve'
                                         'r.cert\nServerKey ssl/serve'
                                         'r.key\nHello world\n',
            '/etc/cups/ssl/server.cert': '',
            '/etc/cups/ssl/server.key': ''
        },
        {
            '/etc/cups/cups-files.conf': 'Hello world\n',
            'ssl-dir': ['/etc/cups/ssl/server.cert',
                        '/etc/cups/ssl/server.key']
        }
    ),
    (
        {
            '/etc/cups/cups-files.conf': 'ServerCertificate ssl/serve'
                                         'r.cert\nServerKey /etc/cups'
                                         '/ssl/server.key\nHello worl'
                                         'd\n',
            '/etc/cups/ssl/server.cert': '',
            '/etc/cups/ssl/server.key': ''
        },
        {
            '/etc/cups/cups-files.conf': 'Hello world\n',
            'ssl-dir': ['/etc/cups/ssl/server.cert',
                        '/etc/cups/ssl/server.key']
        }
    ),
    (
        {
            '/etc/cups/cups-files.conf': 'ServerCertificate ssl/serve'
                                         'r.cert\nServerKey /somewher'
                                         'e/else/server.key\nHello wo'
                                         'rld\n',
            '/etc/cups/ssl/server.cert': '',
            '/somewhere/else/server.key': ''
        },
        {
            '/etc/cups/cups-files.conf': 'Hello world\n',
            'ssl-dir': ['/etc/cups/ssl/server.cert',
                        '/etc/cups/ssl/server.key']
        }
    ),
    (
        {
            '/etc/cups/cups-files.conf': 'ServerCertificate /somewher'
                                         'e/else/server.cert\nServerK'
                                         'ey /etc/cups/ssl/server.key'
                                         '\nHello world\n',
            '/somewhere/else/server.cert': '',
            '/etc/cups/ssl/server.key': ''
        },
        {
            '/etc/cups/cups-files.conf': 'Hello world\n',
            'ssl-dir': ['/etc/cups/ssl/server.key',
                        '/etc/cups/ssl/server.cert']
        }
    ),
    (
        {
            '/etc/cups/cups-files.conf': 'ServerCertificate /somewher'
                                         'e/else/server.cert\nServerK'
                                         'ey /somewhere/else/server.c'
                                         'ert\nHello world\n',
            '/somewhere/else/server.cert': '',
            '/somewhere/else/server.key': ''
        },
        {
            '/etc/cups/cups-files.conf': 'Hello world\n\n# added by L'
                                         'eapp\nServerKeychain /somew'
                                         'here/else\n'
        }
    ),
    (
        {
            '/etc/cups/cups-files.conf': 'ServerCertificate /somewher'
                                         'e/else/server.cert\nServerK'
                                         'ey /anywhere/else/server.ke'
                                         'y\nHello world\n',
            '/somewhere/else/server.cert': '',
            '/anywhere/else/server.key': ''
        },
        {
            '/etc/cups/cups-files.conf': 'Hello world\n',
            'ssl-dir': ['/etc/cups/ssl/server.cert',
                        '/etc/cups/ssl/server.key']
        }
    ),
    (
        {
            '/etc/cups/cups-files.conf': 'ServerCertificate ssl/somedir/'
                                         'server.cert\nHello world\nServ'
                                         'erKey ssl/server.key\n',
            '/etc/cups/ssl/somedir/server.cert': '',
            '/etc/cups/ssl/server.key': ''
        },
        {
            '/etc/cups/cups-files.conf': 'Hello world\n',
            'ssl-dir': ['/etc/cups/ssl/somedir/server.cert',
                        '/etc/cups/ssl/server.key',
                        '/etc/cups/ssl/server.cert']
        }
    ),
    (
        {
            '/etc/cups/cups-files.conf': 'ServerCertificate /etc/cups/ss'
                                         'l/somedir/server.cert\nHello w'
                                         'orld\nServerKey ssl/server.key\n',
            '/etc/cups/ssl/somedir/server.cert': '',
            '/etc/cups/ssl/server.key': ''
        },
        {
            '/etc/cups/cups-files.conf': 'Hello world\n',
            'ssl-dir': ['/etc/cups/ssl/somedir/server.cert',
                        '/etc/cups/ssl/server.key',
                        '/etc/cups/ssl/server.cert']
        }
    )
)


@pytest.mark.parametrize('files,expected', testdata)
def test_migrate_certkey(files, expected):
    op = MockFileSystem(infiles=files)

    migrate_certkey(op)

    assert op.files.get('/etc/cups/cups-files.conf', None) == expected.get('/etc/cups/cups-files.conf', None)
    assert op.ssl_dir == expected.get('ssl-dir', [])
