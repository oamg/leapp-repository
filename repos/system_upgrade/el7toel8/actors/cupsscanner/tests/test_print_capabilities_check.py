import pytest

from leapp.libraries.actor.cupsscanner import print_capabilities_check

testdata = (
    ('\n', False),
    ('Something else\n', False),
    ('#PrintcapFormat smth\n', False),
    ('PrintcapFormat\n', False),
    ('PrintcapFormat smth\n', True)
)


class MockCUPSD(object):
    def __init__(self, content):
        self.content = content

    def read(self, path):
        if path:
            return self.content.splitlines(True)
        return None


@pytest.mark.parametrize("content, expected", testdata)
def test_print_capabilities_check(content, expected):
    config = MockCUPSD(content)

    ret = print_capabilities_check('does_not_matter', config.read)

    assert ret == expected
