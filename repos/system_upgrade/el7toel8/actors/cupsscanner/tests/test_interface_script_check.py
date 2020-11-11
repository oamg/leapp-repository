import pytest

from leapp.libraries.actor.cupsscanner import interface_script_check

testdata = (
    ('bla', [], False),
    ('/etc/cups/interfaces', [], False),
    ('/etc/cups/interfaces', ['smth'], True),
)


class MockFilesystem(object):
    def __init__(self, path, files):
        self.path = path
        self.files = files

    def check_path(self, path):
        if self.path == path:
            return True
        return False

    def list_dir(self, path):
        if self.path == path:
            return self.files
        return []


@pytest.mark.parametrize("path,files,expected", testdata)
def test_interface_script_check(path, files, expected):
    filesystem = MockFilesystem(path, files)

    ret = interface_script_check(filesystem.check_path,
                                 filesystem.list_dir)

    assert ret == expected
