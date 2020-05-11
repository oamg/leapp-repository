import textwrap

from leapp.libraries.actor.removeoldpammodulesscanner import RemoveOldPAMModulesScannerLibrary
from leapp.libraries.common.pam import PAM


def get_config(config):
    return textwrap.dedent(config).strip()


def test_RemoveOldPAMModulesScannerLibrary_process__pkcs11():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_pkcs11.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    obj = RemoveOldPAMModulesScannerLibrary(PAM(pam))
    model = obj.process()
    assert model.modules == ['pam_pkcs11']


def test_RemoveOldPAMModulesScannerLibrary_process__krb5():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_krb5.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    obj = RemoveOldPAMModulesScannerLibrary(PAM(pam))
    model = obj.process()
    assert model.modules == ['pam_krb5']


def test_RemoveOldPAMModulesScannerLibrary_process__all():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_krb5.so
    auth sufficient pam_pkcs11.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    obj = RemoveOldPAMModulesScannerLibrary(PAM(pam))
    model = obj.process()
    assert len(model.modules) == 2
    assert 'pam_krb5' in model.modules
    assert 'pam_pkcs11' in model.modules


def test_RemoveOldPAMModulesScannerLibrary_process__none():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    obj = RemoveOldPAMModulesScannerLibrary(PAM(pam))
    model = obj.process()
    assert not model.modules
