import pytest

from leapp.libraries.actor.cupsscanner import ssl_directive_check

testdata = (
    ('\n', False),
    ('smth\n', False),
    ('#ServerCertificate my.crt\n', False),
    ('#ServerKey my.key\n', False),
    ('ServerCertificate\n', False),
    ('ServerKey\n', False),
    ('ServerKey my.key\n', True),
    ('ServerCertificate my.crt\n', True),
    ('ServerCertificate my.crt\nServerKey my.key\n', True)
)


class MockCupsfiles(object):
    def __init__(self, content):
        self.content = content

    def read(self, path):
        return self.content.splitlines(True)


@pytest.mark.parametrize("content,expected", testdata)
def test_ssl_directive_check(content, expected):
    config = MockCupsfiles(content)

    ret = ssl_directive_check(config.read)

    assert ret == expected
