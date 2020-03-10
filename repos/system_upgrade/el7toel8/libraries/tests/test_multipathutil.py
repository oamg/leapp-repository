import leapp.libraries.common.multipathutil as lib


def test_no_config():
    content = lib.read_config('/this/does/not/exist')
    assert content is None


def test_blank_line():
    data = lib.LineData('', None, False)
    assert data.type == data.TYPE_BLANK
    data = lib.LineData('    ', 'devices', True)
    assert data.type == data.TYPE_BLANK
    data = lib.LineData('# comment at start of line', 'defaults', False)
    assert data.type == data.TYPE_BLANK
    data = lib.LineData('  ! alternate comment method!!!', 'blacklist', True)
    assert data.type == data.TYPE_BLANK
    data = lib.LineData('# } still a comment', None, False)
    assert data.type == data.TYPE_BLANK
    data = lib.LineData('   # "also a comment!"', "multipaths", True)
    assert data.type == data.TYPE_BLANK
    data = lib.LineData(' "ignore lines starting with a string"', None, False)
    assert data.type == data.TYPE_BLANK


def test_section_end():
    data = lib.LineData('}', None, False)
    assert data.type == data.TYPE_SECTION_END
    data = lib.LineData('     }  # trailing comment', 'devices', True)
    assert data.type == data.TYPE_SECTION_END
    data = lib.LineData('     }  JUNK AFTERWARDS', 'defaults', False)
    assert data.type == data.TYPE_SECTION_END
    data = lib.LineData('\t \t}  !!tabs', 'multipaths', True)
    assert data.type == data.TYPE_SECTION_END


def test_section_start():
    sections = ('defaults', 'blacklist', 'blacklist_exceptions', 'devices',
                'overrides', 'multipaths')
    subsections = {'blacklist': 'device', 'blacklist_exceptions': 'device',
                   'devices': 'device', 'multipaths': 'multipath'}
    for section in sections:
        data = lib.LineData(section + ' {', None, False)
        assert data.type == data.TYPE_SECTION_START
        assert data.section == section

    try:
        data = lib.LineData('not_a_section {', None, False)
        assert False
    except ValueError:
        pass

    data = lib.LineData('defaults # works even without brace', None, False)
    assert data.type == data.TYPE_SECTION_START
    assert data.section == 'defaults'

    data = lib.LineData('\t \tmultipaths { # tabs', None, False)
    assert data.type == data.TYPE_SECTION_START
    assert data.section == 'multipaths'

    data = lib.LineData('devices{ # do not need a space', None, False)
    assert data.type == data.TYPE_SECTION_START
    assert data.section == 'devices'

    for section in subsections:
        data = lib.LineData(subsections[section] + ' {', section, False)
        assert data.type == data.TYPE_SECTION_START
        assert data.section == subsections[section]

    data = lib.LineData('devices { # wrong section', 'multipath', False)
    assert data.type != data.TYPE_SECTION_START

    data = lib.LineData('devices { # already in subsection', 'device', True)
    assert data.type != data.TYPE_SECTION_START


def test_option():
    data = lib.LineData('key value', 'defaults', False)
    assert data.type == data.TYPE_OPTION
    assert data.option == 'key'
    assert data.value == 'value'

    data = lib.LineData('key value # comment', 'devices', True)
    assert data.option == 'key'
    assert data.value == 'value'

    data = lib.LineData('    key value "extra string"', 'multipaths', True)
    assert data.option == 'key'
    assert data.value == 'value'

    data = lib.LineData(' \t\tkey "string value" junk', 'blacklist', False)
    assert data.option == 'key'
    assert data.value == 'string value'

    try:
        data = lib.LineData('key  # comment', 'devices', True)
        assert False
    except ValueError:
        pass


def test_enabled():
    values = (('yes', True), ('1', True), ('no', False), ('0', False))
    for value, is_enabled in values:
        data = lib.LineData('key ' + value, 'defaults', False)
        assert data.type == data.TYPE_OPTION
        assert data.option == 'key'
        assert data.value == value
        assert data.is_enabled() == is_enabled

    data = lib.LineData('key neither_yes_nor_no', 'defaults', False)
    assert data.type == data.TYPE_OPTION
    assert data.option == 'key'
    assert data.value == 'neither_yes_nor_no'
    assert data.is_enabled() is None
