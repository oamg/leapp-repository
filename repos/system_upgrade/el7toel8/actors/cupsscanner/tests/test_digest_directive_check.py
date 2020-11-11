import pytest

from leapp.libraries.actor.cupsscanner import digest_directive_check

testdata = (
    ('\n', False),
    ('test\n', False),
    ('AuthType Basic\n', False),
    ('DefaultAuthType Basic\n', False),
    ('#AuthType Digest\n', False),
    ('#DefaultAuthType BasicDigest\n', False),
    ('DefaultAuthType BasicDigest\n', True),
    ('DefaultAuthType Digest\n', True),
    ('AuthType Digest\n', True),
    ('AuthType BasicDigest\n', True),
    ('AuthType BasicDigest\nDefaultAuthType Digest\n', True),
)


class MockConfig(object):
    def __init__(self, content):
        self.content = content

    def read(self, path):
        return self.content.splitlines(True)


@pytest.mark.parametrize("content,expected", testdata)
def test_digest_directive_check(content, expected):
    config = MockConfig(content)

    ret = digest_directive_check('does_not_matter', config.read)

    assert ret == expected
