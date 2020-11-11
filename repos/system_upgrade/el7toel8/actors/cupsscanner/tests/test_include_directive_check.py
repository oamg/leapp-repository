import pytest

from leapp.libraries.actor.cupsscanner import include_directive_check

testdata = (
    (
        {
            '/etc/cups/cupsd.conf': '\n'
        },
        {
            'included_files': ['/etc/cups/cupsd.conf'],
        }
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'Include smth.conf\n',
            'smth.conf': '\n'
        },
        {
            'included_files': ['/etc/cups/cupsd.conf', 'smth.conf'],
        }
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'Include smth.conf\nInclude smb.conf\n',
            'smth.conf': '\n',
            'smb.conf': '\n'
        },
        {
            'included_files': ['/etc/cups/cupsd.conf', 'smth.conf',
                               'smb.conf'],
        }
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'Include smth.conf\n',
            'smth.conf': 'Include smb.conf\n',
            'smb.conf': '\n'
        },
        {
            'included_files': ['/etc/cups/cupsd.conf', 'smth.conf',
                               'smb.conf'],
        }
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'Include smth.conf\n',
            'smth.conf': 'Include smb.conf\n',
            'smb.conf': 'Include any.conf\n',
            'any.conf': '\n'
        },
        {
            'included_files': ['/etc/cups/cupsd.conf', 'smth.conf',
                               'smb.conf', 'any.conf'],
        }
    ),
    (
        {
            '/etc/cups/cupsd.conf': '#Include smth.conf'
        },
        {
            'included_files': ['/etc/cups/cupsd.conf']
        }
    ),
    (
        {
            '/etc/cups/cupsd.conf': 'Include\n'
        },
        {
            'included_files': ['/etc/cups/cupsd.conf'],
        }
    ),
    (
        {
            '/etc/cups/cupsd.conf': '    Include smth.conf smth_more\n',
            'smth.conf': '\n'
        },
        {
            'included_files': ['/etc/cups/cupsd.conf', 'smth.conf']
        }
    )
)


class MockFileSystem(object):
    def __init__(self, infiles):
        self.files = infiles

    def read(self, path):
        if path in self.files.keys():
            return self.files[path].splitlines(True)
        raise IOError('Error during reading file.')


@pytest.mark.parametrize("files,expected", testdata)
def test_include_directive_check(files, expected):
    f = MockFileSystem(files)

    included_files, error_list = include_directive_check(read_func=f.read)

    assert included_files == expected.get('included_files', [])
    assert error_list == expected.get('error_list', [])
