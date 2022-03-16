import pytest

from leapp.libraries.actor.opensshdropindirectory import prepend_string_if_not_present


class MockFile(object):
    def __init__(self, path, content=None):
        self.path = path
        self.content = content
        self.error = False

    def readlines(self):
        return self.content.splitlines(True)

    def seek(self, n):
        self.content = ''

    def write(self, content):
        self.content = content


testdata = (
    ('', 'Prepend', 'Prepend',
        'Prepend'),  # only prepend
    ('Text', '', '',
        'Text'),  # only text
    ('Text', 'Prepend', 'Prepend',
        'PrependText'),  # prepended text
    ('Prepend\nText\n', 'Prepend', 'Prepend',
        'Prepend\nText\n'),  # already present
    ('Text\n', '# Comment\nPrepend\n', 'Prepend',
        '# Comment\nPrepend\nText\n'),  # different prepend than check string
    ('Prepend\nText\n', '# Comment\nPrepend\n', 'Prepend',
        'Prepend\nText\n'),  # different prepend than check string, already present
)


@pytest.mark.parametrize('file_content,prepend,check_string,expected', testdata)
def test_prepend_string_if_not_present(file_content, prepend, check_string, expected):
    f = MockFile('/etc/ssh/sshd_config', file_content)

    prepend_string_if_not_present(f, prepend, check_string)

    assert f.content == expected
