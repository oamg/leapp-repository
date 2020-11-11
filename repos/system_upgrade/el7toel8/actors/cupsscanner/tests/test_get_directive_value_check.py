import pytest

from leapp.libraries.actor.cupsscanner import get_directive_value

testdata = (
    ('Include', 'Include smth', 'smth'),
    ('Include', 'something_else', None),
    ('Include', 'Include', ''),
    ('Include', '#Include smth', None),
    ('Include', '   Include smth', 'smth'),
    ('Include', '   Include smth anything', 'smth'),
)


@pytest.mark.parametrize('string, line, expected', testdata)
def test_get_directive_value(string, line, expected):

    value = get_directive_value(string, line)

    assert value == expected
