import pytest

from leapp.libraries.actor.cupsscanner import environment_setup_check

testdata = (
    ('\n', False),
    ('Something else\n', False),
    ('#PassEnv smth\n', False),
    ('   #SetEnv smth\n', False),
    ('PassEnv smth\n', True),
    ('SetEnv smth\n', True),
    ('PassEnv\n', False),
    ('SetEnv\n', False),
    ('PassEnv smth\nSetEnv smth\n', True)
)


class MockCUPSD(object):
    def __init__(self, content):
        self.content = content

    def read(self, path):
        if path:
            return self.content.splitlines(True)
        return None


@pytest.mark.parametrize("content, expected", testdata)
def test_environment_setup_check(content, expected):
    config = MockCUPSD(content)

    ret = environment_setup_check('does_not_matter', config.read)

    assert ret == expected
