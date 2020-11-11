import pytest

from leapp.libraries.actor.cupsmigrate import migrate_configuration
from leapp.models import CupsChangedFeatures


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


class MockLogger(object):
    def __init__(self):
        self.debug_msg = ''
        self.error_msg = ''

    def debug_log(self, msg):
        self.debug_msg += msg

    def error_log(self, msg):
        self.error_msg += msg


class MockModel(object):
    def __init__(self, facts):
        if not facts:
            self.model = None
            return

        self.model = CupsChangedFeatures(include=facts.get('include', False),
                                         digest=facts.get('digest', False),
                                         env=facts.get('env', False),
                                         certkey=facts.get('certkey', False),
                                         printcap=facts.get('printcap', False),
                                         include_files=facts.get('include_files', []))

    def get_facts(self, model):
        return self.model


testdata = (
    (
        None,
        {
            'debug_msg': '',
            'error_msg': ''
        }
    ),
    (
        {},
        {
            'debug_msg': '',
            'error_msg': ''
        }
    ),
    (
        {
            'include': True,
            'include_files': ['/etc/cups/cupsd.conf', 'smth.conf',
                              'any.conf'],
        },
        {
            'debug_msg': 'Migrating CUPS configuration - Include directives.',
            'error_msg': 'Following errors happened during CUPS migration:\n   '
                         '- Include directive: Error when reading file /etc/cup'
                         's/cupsd.conf - file does not exist.\n   - Include dir'
                         'ective: Error when reading file smth.conf - file does'
                         ' not exist.\n   - Include directive: Error when readi'
                         'ng file any.conf - file does not exist.'
        }
    ),
    (
        {
            'digest': True,
        },
        {
            'debug_msg': 'Migrating CUPS configuration - BasicDigest/Digest'
                         ' directives.',
            'error_msg': 'Following errors happened during CUPS migration:\n   '
                         '- Digest/BasicDigest values: Error when reading file '
                         '/etc/cups/cupsd.conf - file does not exist.'
        }
    ),
    (
        {
            'env': True,
        },
        {
            'debug_msg': 'Migrating CUPS configuration - PassEnv/SetEnv directives.',
            'error_msg': 'Following errors happened during CUPS migration:\n   '
                         '- PassEnv/SetEnv directives: Error when reading file '
                         '/etc/cups/cupsd.conf - file does not exist.'
        }
    ),
    (
        {
            'certkey': True,
        },
        {
            'debug_msg': 'Migrating CUPS configuration - ServerKey/ServerCertif'
                         'icate directive.',
            'error_msg': 'Following errors happened during CUPS migration:\n   '
                         '- ServerKey/ServerCertificate directives: Error when '
                         'reading file /etc/cups/cups-files.conf - file does no'
                         't exist.'
        }
    ),
    (
        {
            'printcap': True,
        },
        {
            'debug_msg': 'Migrating CUPS configuration - PrintcapFormat directive.',
            'error_msg': 'Following errors happened during CUPS migration:\n   '
                         '- PrintcapFormat directive: Error when reading file /'
                         'etc/cups/cupsd.conf - file does not exist.'
        }
    ),
    (
        {
            'certkey': True,
            'include': True,
            'env': True,
            'printcap': True,
            'digest': True,
            'include_files': ['/etc/cups/cupsd.conf', 'smth.conf',
                              'any.conf']
        },
        {
            'debug_msg': 'Migrating CUPS configuration - Include directives.Mig'
                         'rating CUPS configuration - BasicDigest/Digest direct'
                         'ives.Migrating CUPS configuration - PassEnv/SetEnv di'
                         'rectives.Migrating CUPS configuration - ServerKey/Ser'
                         'verCertificate directive.Migrating CUPS configuration'
                         ' - PrintcapFormat directive.',
            'error_msg': 'Following errors happened during CUPS migration:\n   '
                         '- Include directive: Error when reading file /etc/cup'
                         's/cupsd.conf - file does not exist.\n   - Include dir'
                         'ective: Error when reading file smth.conf - file does'
                         ' not exist.\n   - Include directive: Error when readi'
                         'ng file any.conf - file does not exist.\n   - Digest/'
                         'BasicDigest values: Error when reading file /etc/cups'
                         '/cupsd.conf - file does not exist.\n   - PassEnv/SetE'
                         'nv directives: Error when reading file /etc/cups/cups'
                         'd.conf - file does not exist.\n   - ServerKey/ServerC'
                         'ertificate directives: Error when reading file /etc/c'
                         'ups/cups-files.conf - file does not exist.\n   - Prin'
                         'tcapFormat directive: Error when reading file /etc/cu'
                         'ps/cupsd.conf - file does not exist.'
        }
    )
)


@pytest.mark.parametrize('facts,expected', testdata)
def test_migrate_configuration(facts, expected):
    data_model = MockModel(facts)

    op = MockFileSystem({})

    logger = MockLogger()

    migrate_configuration(logger.error_log,
                          logger.debug_log,
                          op,
                          data_model.get_facts)

    assert logger.debug_msg == expected['debug_msg']
    assert logger.error_msg == expected['error_msg']
