import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor.cupsscanner import find_features

message = 'Checking if CUPS configuration contains removed features.'

testdata = (
    (
        ['ble'],
        {},
        {}
    ),
    (
        ['cups'],
        {
            '/etc/cups/cupsd.conf': '',
            '/etc/cups/cups-files.conf': ''
        },
        {
            'debug': message
        }
    ),
    (
        ['cups'],
        {
            '/etc/cups/cupsd.conf': 'Include smth\n',
            '/etc/cups/cups-files.conf': '',
            'smth': ''
        },
        {
            'include': True,
            'digest': False,
            'interface': False,
            'env': False,
            'certkey': False,
            'printcap': False,
            'included_files': ['/etc/cups/cupsd.conf', 'smth'],
            'debug': message
        }
    ),
    (
        ['cups'],
        {
            '/etc/cups/cupsd.conf': 'Include smth\n',
            '/etc/cups/cups-files.conf': '',
        },
        {
            'debug': message,
            'warn': 'Following included files will not be appended to cupsd.c'
            'onf due attached error:\n   - Error during reading file smth: file not found'
        }
    ),
    (
        ['cups'],
        {
            '/etc/cups/cupsd.conf': 'Include smth\nInclude smb\n',
            '/etc/cups/cups-files.conf': '',
            'smth': '',
            'smb': ''
        },
        {
            'include': True,
            'digest': False,
            'interface': False,
            'env': False,
            'certkey': False,
            'printcap': False,
            'included_files': ['/etc/cups/cupsd.conf', 'smth', 'smb'],
            'debug': message
        }
    ),
    (
        ['cups'],
        {
            '/etc/cups/cupsd.conf': 'Include smth\n',
            '/etc/cups/cups-files.conf': '',
            'smth': 'AuthType Digest\nPassEnv smth\nPrintcapFormat neco\n'
        },
        {
            'include': True,
            'digest': True,
            'interface': False,
            'env': True,
            'certkey': False,
            'printcap': True,
            'included_files': ['/etc/cups/cupsd.conf', 'smth'],
            'debug': message
        }
    ),
    (
        ['cups'],
        {
            '/etc/cups/cupsd.conf': '',
            '/etc/cups/cups-files.conf': 'ServerKey smth.key\n',
            'smth.key': ''
        },
        {
            'include': False,
            'digest': False,
            'interface': False,
            'env': False,
            'certkey': True,
            'printcap': False,
            'included_files': ['/etc/cups/cupsd.conf'],
            'debug': message
        }
    ),
    (
        ['cups'],
        {
            '/etc/cups/cupsd.conf': '',
            '/etc/cups/cups-files.conf': 'ServerCertificate smth.cert\n',
            'smth.cert': ''
        },
        {
            'include': False,
            'digest': False,
            'interface': False,
            'env': False,
            'certkey': True,
            'printcap': False,
            'included_files': ['/etc/cups/cupsd.conf'],
            'debug': message
        }
    ),
    (
        ['cups'],
        {
            '/etc/cups/cupsd.conf': '',
            '/etc/cups/cups-files.conf': 'ServerKey smth.key\n'
                                         'ServerCertificate smth.cert\n',
            'smth.key': '',
            'smth.cert': ''
        },
        {
            'include': False,
            'digest': False,
            'interface': False,
            'env': False,
            'certkey': True,
            'printcap': False,
            'included_files': ['/etc/cups/cupsd.conf'],
            'debug': message
        }
    ),
    (
        ['cups'],
        {
            '/etc/cups/cupsd.conf': 'AuthType Digest\n',
            '/etc/cups/cups-files.conf': '',
        },
        {
            'include': False,
            'digest': True,
            'interface': False,
            'env': False,
            'certkey': False,
            'printcap': False,
            'included_files': ['/etc/cups/cupsd.conf'],
            'debug': message
        }
    ),
    (
        ['cups'],
        {
            '/etc/cups/cupsd.conf': 'DefaultAuthType BasicDigest\n',
            '/etc/cups/cups-files.conf': '',
        },
        {
            'include': False,
            'digest': True,
            'interface': False,
            'env': False,
            'certkey': False,
            'printcap': False,
            'included_files': ['/etc/cups/cupsd.conf'],
            'debug': message
        }
    ),
    (
        ['cups'],
        {
            '/etc/cups/cupsd.conf': 'PassEnv smth\n',
            '/etc/cups/cups-files.conf': '',
        },
        {
            'include': False,
            'digest': False,
            'interface': False,
            'env': True,
            'certkey': False,
            'printcap': False,
            'included_files': ['/etc/cups/cupsd.conf'],
            'debug': message
        }
    ),
    (
        ['cups'],
        {
            '/etc/cups/cupsd.conf': 'SetEnv smth\n',
            '/etc/cups/cups-files.conf': '',
        },
        {
            'include': False,
            'digest': False,
            'interface': False,
            'env': True,
            'certkey': False,
            'printcap': False,
            'included_files': ['/etc/cups/cupsd.conf'],
            'debug': message
        }
    ),
    (
        ['cups'],
        {
            '/etc/cups/cupsd.conf': 'PrintcapFormat smth\n',
            '/etc/cups/cups-files.conf': '',
        },
        {
            'include': False,
            'digest': False,
            'interface': False,
            'env': False,
            'certkey': False,
            'printcap': True,
            'included_files': ['/etc/cups/cupsd.conf'],
            'debug': message
        }
    ),
    (
        ['cups'],
        {
            '/etc/cups/cupsd.conf': '',
            '/etc/cups/cups-files.conf': '',
            '/etc/cups/interfaces': []
        },
        {
            'debug': message
        }
    ),
    (
        ['cups'],
        {
            '/etc/cups/cupsd.conf': '',
            '/etc/cups/cups-files.conf': '',
            '/etc/cups/interfaces': ['smth', 'anything'],
            'smth': '',
            'anything': ''
        },
        {
            'include': False,
            'digest': False,
            'interface': True,
            'env': False,
            'certkey': False,
            'printcap': False,
            'included_files': ['/etc/cups/cupsd.conf'],
            'debug': message
        }
    ),
    (
        ['cups'],
        {
            '/etc/cups/cupsd.conf': 'Include mst\nAuthType Digest\n'
                                    'PassEnv too\nPrintcapFormat poo\n',
            '/etc/cups/cups-files.conf': 'ServerKey my.key\n'
                                         'ServerCertificate my.cert\n',
            '/etc/cups/interfaces': ['smth', 'anything'],
            'smth': '',
            'anything': '',
            'mst': ''
        },
        {
            'include': True,
            'digest': True,
            'interface': True,
            'env': True,
            'certkey': True,
            'printcap': True,
            'included_files': ['/etc/cups/cupsd.conf', 'mst'],
            'debug': message
        }
    )
)


class MockActor(object):
    def __init__(self):
        self.output = {}

    def send_features(self, interface, digest, include, certkey, env,
                      printcap, included_files):
        self.output['interface'] = interface
        self.output['digest'] = digest
        self.output['include'] = include
        self.output['certkey'] = certkey
        self.output['env'] = env
        self.output['printcap'] = printcap
        self.output['included_files'] = included_files


class MockLogger(object):
    def __init__(self):
        self.debugmsg = ''
        self.warnmsg = ''
        self.errormsg = ''

    def debug(self, message):
        self.debugmsg += message

    def error(self, message):
        self.errormsg += message

    def warn(self, message):
        self.warnmsg += message


class MockFileSystem(object):
    def __init__(self, packages, files):
        self.installed_packages = packages
        self.files = files

    def is_installed(self, pkg):
        if pkg in self.installed_packages:
            return True
        return False

    def read(self, path):
        if path in self.files.keys():
            return self.files[path].splitlines(True)
        raise IOError('Error during reading file {} - file'
                      ' not found.'.format(path))

    def path_exists(self, path):
        if path in self.files.keys():
            return True
        return False

    def list_dir(self, path):
        if path in self.files.keys():
            return self.files[path]
        return False


def test_find_features_exception():
    logger = MockLogger()
    system = MockFileSystem(['cups'], {})
    actor = MockActor()

    with pytest.raises(StopActorExecutionError):
        find_features(logger.debug,
                      logger.warn,
                      logger.error,
                      actor.send_features,
                      system.is_installed,
                      system.read,
                      system.path_exists,
                      system.list_dir)


@pytest.mark.parametrize(("packages,files,expected"), testdata)
def test_find_features(packages, files, expected):
    logger = MockLogger()
    system = MockFileSystem(packages, files)
    actor = MockActor()

    find_features(logger.debug,
                  logger.warn,
                  logger.error,
                  actor.send_features,
                  system.is_installed,
                  system.read,
                  system.path_exists,
                  system.list_dir)

    assert actor.output.get('interface', None) == expected.get('interface', None)
    assert actor.output.get('digest', None) == expected.get('digest', None)
    assert actor.output.get('include', None) == expected.get('include', None)
    assert actor.output.get('certkey', None) == expected.get('certkey', None)
    assert actor.output.get('env', None) == expected.get('env', None)
    assert actor.output.get('printcap', None) == expected.get('printcap', None)
    assert actor.output.get('included_files', None) == expected.get('included_files', None)
    assert logger.debugmsg == expected.get('debug', '')
    assert logger.warnmsg == expected.get('warn', '')
    assert logger.errormsg == expected.get('error', '')
