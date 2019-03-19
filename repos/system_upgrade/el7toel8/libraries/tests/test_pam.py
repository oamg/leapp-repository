import textwrap

from leapp.libraries.common.pam import PAM


def get_config(config):
    return textwrap.dedent(config).strip()


def test_PAM_parse():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    obj = PAM('')
    modules = obj.parse(pam)

    assert len(modules) == 3
    assert 'pam_unix' in modules
    assert 'pam_sss' in modules
    assert 'pam_deny' in modules


def test_PAM_has__true():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    obj = PAM(pam)
    assert obj.has('pam_unix')
    assert obj.has('pam_sss')
    assert obj.has('pam_deny')


def test_PAM_has__false():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    obj = PAM(pam)
    assert not obj.has('pam_winbind')


def test_PAM_has_unknown_module__empty():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    obj = PAM(pam)
    assert obj.has_unknown_module([])


def test_PAM_has_unknown_module__false():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    obj = PAM(pam)
    assert not obj.has_unknown_module(['pam_unix', 'pam_sss', 'pam_deny'])


def test_PAM_has_unknown_module__true():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    session pam_ecryptfs.so
    ''')

    obj = PAM(pam)
    assert obj.has_unknown_module(['pam_unix', 'pam_sss', 'pam_deny'])


def test_PAM_read_file__non_existent():
    content = PAM.read_file('/this/does/not/exist')
    assert content == ''


def test_PAM_read_file__ok():
    content = PAM.read_file(__file__)
    assert content != ''
    assert 'test_PAM_read_file__ok' in content
