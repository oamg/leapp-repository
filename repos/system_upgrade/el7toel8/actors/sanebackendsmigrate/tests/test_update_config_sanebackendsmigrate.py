import pytest

from leapp.libraries.actor.sanebackendsmigrate import (
    CANON,
    CANON_DR,
    CARDSCAN,
    DLL,
    EPJITSU,
    FUJITSU,
    update_config,
    XEROX_MFP
)


def _pattern_exists(content, macro):
    for line in content.split('\n'):
        if line.lstrip().startswith(macro):
            return True
    return False


def _create_original_file(file_content):
    content = ''
    for line in file_content:
        fmt_line = '{}\n'.format(line)
        content += fmt_line
    return content


def _create_expected_file(original_content, new_content):
    macros = []
    for line in new_content:
        if not _pattern_exists(original_content, line):
            macros.append(line)

    fmt_input = ''
    if macros:
        fmt_input = "\n{comment_line}\n{content}\n".format(comment_line='# content added by Leapp',
                                                           content='\n'.join(macros))

    return '\n'.join((original_content, fmt_input))


testdata = [
    (
        _create_original_file(['']),
        _create_expected_file('', CANON),
        CANON
    ),
    (
        _create_original_file(['']),
        _create_expected_file('', CANON_DR),
        CANON_DR
    ),
    (
        _create_original_file(['']),
        _create_expected_file('', CARDSCAN),
        CARDSCAN
    ),
    (
        _create_original_file(['']),
        _create_expected_file('', DLL),
        DLL
    ),
    (
        _create_original_file(['']),
        _create_expected_file('', EPJITSU),
        EPJITSU
    ),
    (
        _create_original_file(['']),
        _create_expected_file('', FUJITSU),
        FUJITSU
    ),
    (
        _create_original_file(['']),
        _create_expected_file('', XEROX_MFP),
        XEROX_MFP
    ),
    (
        _create_original_file(['fdfdfdr']),
        _create_expected_file('fdfdfdr', CANON),
        CANON
    ),
    (
        _create_original_file(['fdfdfdr']),
        _create_expected_file('fdfdfdr', CANON_DR),
        CANON_DR
    ),
    (
        _create_original_file(['fdfdfdr']),
        _create_expected_file('fdfdfdr', CARDSCAN),
        CARDSCAN
    ),
    (
        _create_original_file(['fdfdfdr']),
        _create_expected_file('fdfdfdr', DLL),
        DLL
    ),
    (
        _create_original_file(['fdfdfdr']),
        _create_expected_file('fdfdfdr', EPJITSU),
        EPJITSU
    ),
    (
        _create_original_file(['fdfdfdr']),
        _create_expected_file('fdfdfdr', FUJITSU),
        FUJITSU
    ),
    (
        _create_original_file(['fdfdfdr']),
        _create_expected_file('fdfdfdr', XEROX_MFP),
        XEROX_MFP
    ),
    (
        _create_original_file(['usb 0x04a9 0x2214']),
        _create_expected_file('usb 0x04a9 0x2214', CANON),
        CANON
    ),
    (
        _create_original_file(['usb 0x1083 0x162c']),
        _create_expected_file('usb 0x1083 0x162c', CANON_DR),
        CANON_DR
    ),
    (
        _create_original_file(['usb 0x0451 0x6250']),
        _create_expected_file('usb 0x0451 0x6250', CARDSCAN),
        CARDSCAN
    ),
    (
        _create_original_file(['#usb 0x0451 0x6250']),
        _create_expected_file('#usb 0x0451 0x6250', CARDSCAN),
        CARDSCAN
    ),
    (
        _create_original_file(['epsonds']),
        _create_expected_file('epsonds', DLL),
        DLL
    ),
    (
        _create_original_file(['usb 0x04c5 0x11bd']),
        _create_expected_file('usb 0x04c5 0x11bd', EPJITSU),
        EPJITSU
    ),
    (
        _create_original_file(['usb 0x04c5 0x132c']),
        _create_expected_file('usb 0x04c5 0x132c', FUJITSU),
        FUJITSU
    ),
    (
        _create_original_file(['usb 0x04e8 0x3471']),
        _create_expected_file('usb 0x04e8 0x3471', XEROX_MFP),
        XEROX_MFP
    ),
    (
        _create_original_file(CANON),
        _create_original_file(CANON),
        CANON
    ),
    (
        _create_original_file(CANON_DR),
        _create_original_file(CANON_DR),
        CANON_DR
    ),
    (
        _create_original_file(CARDSCAN),
        _create_original_file(CARDSCAN),
        CARDSCAN
    ),
    (
        _create_original_file(DLL),
        _create_original_file(DLL),
        DLL
    ),
    (
        _create_original_file(EPJITSU),
        _create_original_file(EPJITSU),
        EPJITSU
    ),
    (
        _create_original_file(FUJITSU),
        _create_original_file(FUJITSU),
        FUJITSU
    ),
    (
        _create_original_file(XEROX_MFP),
        _create_original_file(XEROX_MFP),
        XEROX_MFP
    )
]
"""
3-tuple of original file, file after migration and list of lines which
will be tried to add
"""


class MockFile(object):
    def __init__(self, path, content=None):
        self.path = path
        self.content = content
        self.error = False

    def append(self, path, content):
        if path != self.path:
            self.error = True
        if not self.error:
            self.content += content
            return self.content
        raise IOError('Error during writing to file: {}.'.format(path))

    def exists(self, path, macro):
        for line in self.content.split('\n'):
            if line.lstrip().startswith(macro) and self.path == path:
                return True
        return False


def test_update_config_file_errors():
    path = 'foo'
    new_content = ['fdfgdfg', 'gnbfgnf']

    f = MockFile(path, content='')

    with pytest.raises(IOError):
        update_config('bar', new_content, f.exists, f.append)

    assert f.content == ''


@pytest.mark.parametrize('orig_content,expected_result,content_to_add', testdata)
def test_update_config_append_into_file(orig_content,
                                        expected_result,
                                        content_to_add):
    f = MockFile('foo', orig_content)

    update_config('foo', content_to_add, f.exists, f.append)

    assert f.content == expected_result
