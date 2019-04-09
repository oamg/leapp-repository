import logging
import os
import os.path as ph

import pytest

from leapp.libraries.actor.openldap import Openldap
from leapp.libraries.actor.nss import Nss
from leapp.libraries.actor.utils import (
    NotNSSConfiguration,
)

from conftest import mock, CONFS

log = logging.getLogger('testing')

NONEXISTENT = 'non-existent-dir'
OUTDIR = 'outdir'


def test_certutil_get_certs(mock):
    with pytest.raises(NotNSSConfiguration):
        Nss.certutil_get_certs(NONEXISTENT)

    assert Nss.certutil_get_certs(mock[0]['nopass'][0])


@pytest.mark.parametrize('config_name', CONFS.keys())
def test_converts_cleanly(config_name, tmpdir, mock):
    ol = Openldap(log)
    conf = ol.TLSConfiguration(*mock[0][config_name])
    outdir = str(tmpdir.join(OUTDIR))
    ol.convert(conf, outdir)
    assert ph.exists(ph.join(outdir, 'cert.pem'))
    assert ph.exists(ph.join(outdir, 'key.pem'))
    assert ph.exists(ph.join(outdir, 'cacerts/0000.pem'))


@pytest.mark.parametrize('config_name, config_override, exception, match', [
    ('pass', (None, None, 'wrong-pass-file'), RuntimeError, r'SEC_ERROR_BAD_PASSWORD'),
    ('pass', (None, 'Wrong-Name', None), RuntimeError, r'Could not find cert')
])
def test_convert_raises(config_name, config_override, exception, match, tmpdir, mock):
    config = [(override if override is not None else conf) 
              for conf, override in zip(mock[0][config_name], config_override)]
    ol = Openldap(log)
    conf = ol.TLSConfiguration(*config)
    outdir = tmpdir.join(OUTDIR)
    with pytest.raises(exception, match=match):
        ol.convert(conf, outdir)


@pytest.mark.parametrize('before, after, asserts', [
    ("""#1

#2
tls_cacertdir {cacertdir}
tls_cert {cert}
tls_key {pinfile}
#3
""", """#1

#2
TLS_CACERTDIR {outdir}/cacerts
TLS_CERT {outdir}/cert.pem
TLS_KEY {outdir}/key.pem
#3
""",
     ['cacerts', 'cert']),
    ("""tls_cacertdir {cacertdir}
""", """TLS_CACERTDIR {outdir}/cacerts
""",
     ['cacerts'])
])
def test_sanity(before, after, asserts, tmpdir, mock):
    confs, nssdb_files = mock

    cnf_cacertdir, cnf_cert, cnf_pinfile = confs['pass']

    ldapconf_path = str(tmpdir.join('ldap.conf'))
    with open(ldapconf_path, 'w') as f:
        f.write(before.format(cacertdir=cnf_cacertdir, cert=cnf_cert, pinfile=cnf_pinfile))

    outdir = tmpdir.join(OUTDIR)

    ol = Openldap(log, confpath=ldapconf_path)
    old = ol._read_ldap_conf()
    new = ol.convert(old, outdir)
    ol._fix_ldap_conf(new)

    def assert_props(our, their):
        assert os.stat(our).st_size != 0
        assert os.stat(their).st_size != 0
        assert os.stat(their).st_uid == os.stat(our).st_uid
        assert os.stat(their).st_gid == os.stat(our).st_gid
        assert os.stat(their).st_mode & 0o777 == os.stat(our).st_mode & 0o777

    assertion = 'cacerts' in asserts
    assert assertion == ph.exists(ph.join(str(outdir), 'cacerts/0000.pem'))
    if assertion:
        assert_props(str(outdir), cnf_cacertdir)
        assert_props(ph.join(str(outdir), 'cacerts'), cnf_cacertdir)
        assert_props(ph.join(str(outdir), 'cacerts/0000.pem'), ph.join(cnf_cacertdir, nssdb_files[0]))

    assertion = 'cert' in asserts
    assert assertion == ph.exists(ph.join(str(outdir), 'cert.pem'))
    assert assertion == ph.exists(ph.join(str(outdir), 'key.pem'))
    if assertion:
        for a, b in [(ph.join(str(outdir), 'cert.pem'), ph.join(cnf_cacertdir, nssdb_files[0]))]:
            assert_props(a, b)

    with open(ldapconf_path, 'r') as f:
        assert f.read() == after.format(outdir=outdir)
