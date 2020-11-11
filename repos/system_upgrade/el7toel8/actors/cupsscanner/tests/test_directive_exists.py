import pytest

from leapp.libraries.actor.cupsscanner import directive_exists

testdata = (
    ('PrintcapFormat', 'ble', False),
    ('PrintcapFormat', '', False),
    ('PrintcapFormat', '#PrintcapFormat', False),
    ('PrintcapFormat', 'PrintcapFormat', True),
    ('PrintcapFormat', '    PrintcapFormat', True)
)


@pytest.mark.parametrize("string, line, expected", testdata)
def test_directive_exists(string, line, expected):

    ret = directive_exists(string, line)

    assert ret == expected
