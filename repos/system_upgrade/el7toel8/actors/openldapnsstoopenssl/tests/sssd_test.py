# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import logging

from leapp.libraries.actor.openldap import Openldap
from leapp.libraries.actor.sssd import Sssd, SssdDomains, SssdServices
import pytest

LOG = logging.getLogger('testing')

SSSDCONF = """[domain/default]
id_provider = ldap
ldap_tls_cacertdir = test

[domain/privs]
id_provider = ldap
ldap_tls_cert = a
ldap_tls_key = b

[domain/noidprovider]
id_provider = ldap
ldap_tls_cert = a
ldap_tls_key = b
"""


def common(tmpdir, cls, new_content):
    conf_file = str(tmpdir.join('sssd.conf'))
    with open(conf_file, 'w') as f:
        f.write(new_content)
    s = Sssd(LOG, conf_file)
    ss = cls(LOG, s.sssd_module, s._sssd, s._ol)
    return ss._read()


def test_read_sssd_domains(tmpdir):
    conf = {'default': Openldap.TLSConfiguration(cacertdir='test', cert=None, key=None),
            'noidprovider': Openldap.TLSConfiguration(cacertdir=None, cert='a', key='b'),
            'privs': Openldap.TLSConfiguration(cacertdir=None, cert='a', key='b')}
    assert common(tmpdir, SssdDomains, SSSDCONF) == conf


@pytest.mark.parametrize('config, result', [
    ('',
     {('pam', 'pam_cert_db_path'): None, ('ssh', 'ca_db'): None}),
    ('[pam]\n[ssh]\n',
     {('pam', 'pam_cert_db_path'): None, ('ssh', 'ca_db'): None}),
    ('[pam]\npam_cert_db_path = abc\n[ssh]\nca_db = def\n',
     {('pam', 'pam_cert_db_path'): 'abc', ('ssh', 'ca_db'): 'def'})
], ids=['empty', 'vacant', 'set'])
def test_read_sssd_services(tmpdir, config, result):
    assert common(tmpdir, SssdServices, config) == result


@pytest.mark.parametrize('cls, new_conf', [
    (SssdDomains, {'default': Openldap.TLSConfiguration(cacertdir='test-d', cert=None, key=None),
                   'noidprovider': Openldap.TLSConfiguration(cacertdir='blah', cert='c', key='d'),
                   'privs': Openldap.TLSConfiguration(cacertdir=None, cert='e', key='f')}),
    (SssdServices, {('pam', 'pam_cert_db_path'): 'abc', ('ssh', 'ca_db'): 'def'})
], ids=['SssdDomains', 'SssdServices'])
def test_fix_sssd(tmpdir, cls, new_conf):
    common(tmpdir, SssdDomains, SSSDCONF)

    conf_file = str(tmpdir.join('sssd.conf'))
    s = Sssd(LOG, conf_file)
    cls(LOG, s.sssd_module, s._sssd, s._ol)._fix(new_conf)

    s = Sssd(LOG, conf_file)
    stored_conf = cls(LOG, s.sssd_module, s._sssd, s._ol)._read()
    assert stored_conf == new_conf
