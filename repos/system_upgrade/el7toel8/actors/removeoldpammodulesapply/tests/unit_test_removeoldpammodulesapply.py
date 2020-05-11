import textwrap

from leapp.libraries.actor.removeoldpammodulesapply import comment_modules, read_file


def get_config(config):
    return textwrap.dedent(config).strip()


def test_read_file__non_existent():
    content = read_file('/this/does/not/exist')
    assert content == ''


def test_read_file__ok():
    content = read_file(__file__)
    assert content != ''
    assert 'test_read_file__ok' in content


def test_comment_modules__none():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_pkcs11.so
    auth sufficient pam_krb5.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')
    expected = pam

    content = comment_modules([], pam)
    assert content == expected


def test_comment_modules__replaced_single():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_pkcs11.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')
    expected = get_config('''
    auth sufficient pam_unix.so
    #auth sufficient pam_pkcs11.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    content = comment_modules(['pam_pkcs11', 'pam_krb5'], pam)
    assert content == expected


def test_comment_modules__replaced_all():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_pkcs11.so
    auth sufficient pam_krb5.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')
    expected = get_config('''
    auth sufficient pam_unix.so
    #auth sufficient pam_pkcs11.so
    #auth sufficient pam_krb5.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    content = comment_modules(['pam_pkcs11', 'pam_krb5'], pam)
    assert content == expected
