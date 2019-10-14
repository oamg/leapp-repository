import leapp.libraries.common.spamassassinutils as lib


def test_parse_sysconfig_spamassassin_begins_with_assignment():
    content = 'SPAMDOPTIONS="foo"\n# bar\n'
    pre, assignment, post = lib.parse_sysconfig_spamassassin(content)
    assert pre == ''
    assert assignment == 'SPAMDOPTIONS="foo"'
    assert post == '# bar\n'


def test_parse_sysconfig_spamassassin_ends_with_assignment():
    content = '# bar\nSPAMDOPTIONS="foo"\n'
    pre, assignment, post = lib.parse_sysconfig_spamassassin(content)
    assert pre == '# bar'
    assert assignment == 'SPAMDOPTIONS="foo"'
    assert post == ''


def test_parse_sysconfig_spamassassin_only_assignment():
    content = 'SPAMDOPTIONS="foo"\n'
    pre, assignment, post = lib.parse_sysconfig_spamassassin(content)
    assert pre == ''
    assert assignment == 'SPAMDOPTIONS="foo"'
    assert post == ''


def test_parse_sysconfig_spamassassin_no_assignment():
    content = '# foo\n'
    pre, assignment, post = lib.parse_sysconfig_spamassassin(content)
    assert pre == '# foo\n'
    assert assignment == ''
    assert post == ''


def test_parse_sysconfig_spamassassin_empty():
    content = ''
    pre, assignment, post = lib.parse_sysconfig_spamassassin(content)
    assert pre == ''
    assert assignment == ''
    assert post == ''
