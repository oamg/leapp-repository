#!/usr/bin/env python3
import subprocess as sp
import os
import os.path as ph
import re
import fileinput
import shutil
from distutils.spawn import find_executable
from collections import namedtuple

from utils import (
    copy_permissions,
    AlreadyConverted,
    InsufficientTooling,
    NotNSSConfiguration,
    UMASK
)
from nss import Nss



class Openldap(object):
    # (<directory>, <pem-file>, <pem-file>)
    # (<directory>, <cert-name>, <pin-file>)
    TLSConfiguration = namedtuple('TLSConfiguration', ['cacertdir', 'cert', 'key'])

    def __init__(self, logger, confpath=None):
        self.log = logger
        self.confpath = confpath if confpath else '/etc/openldap/ldap.conf'

    def convert(self, conf, outdir=None):
        if not conf.cacertdir:
            raise NotNSSConfiguration('CACERTDIR is empty')

        self._test_tooling()

        target_folder = str(outdir) or (conf.cacertdir.strip() + '~leapp-migrated')
        if os.path.exists(target_folder):
            raise AlreadyConverted('Target extraction directory already exists: `%s`' % (target_folder))

        old_umask = os.umask(UMASK)
        try:
            os.mkdir(target_folder)
            copy_permissions(conf.cacertdir, target_folder)
        except BaseException as e:
            raise RuntimeError('Could not create directory for extracted certificates, the error was: %s' % e)
        finally:
            os.umask(old_umask)

        if conf.cert:
            cert_out = ph.join(target_folder, 'cert.pem')
            Nss.export_cert(conf.cacertdir, conf.cert, cert_out)
            assert os.stat(cert_out).st_size != 0

            key_out = ph.join(target_folder, 'key.pem')
            Nss.export_key(conf.cacertdir, conf.cert, conf.key, key_out)
            assert os.stat(key_out).st_size != 0

        Nss.export_ca_certs(conf.cacertdir, ph.join(target_folder, 'cacerts'))

        return self.TLSConfiguration(ph.join(target_folder, 'cacerts'),
                                     ph.join(target_folder, 'cert.pem'),
                                     ph.join(target_folder, 'key.pem'))

    def _process_line(self, line, fn, conf):
        rx = re.compile(r'^(\w+)[ \t]+(.+)$')
        try:
            m = re.match(rx, line).groups()
        except AttributeError:
            return None
        normalized = m[0].lower()[4:]  # dropping TLS_ prefix
        if normalized in conf._fields:
            return fn(normalized, m[1], conf)
        else:
            return None

    def _read_ldap_conf(self):
        def fn(attr, value, conf):
            return {attr: value.strip()}

        with open(self.confpath, 'r') as f:
            lines = f.readlines()
        conf = self.TLSConfiguration(None, None, None)
        for l in lines:
            new = self._process_line(l, fn, conf)
            if new:
                conf = conf._replace(**new)
        return conf

    def _fix_ldap_conf(self, conf):
        def fn(attr, value, conf):
            new_attr = 'TLS_' + attr.upper()
            new_value = conf._asdict()[attr]
            return '{} {}'.format(new_attr, new_value)

        f = fileinput.input(self.confpath, inplace=True)
        for line in f:
            res = self._process_line(line, fn, conf)
            if res is not None:
                print(res)
            else:
                print(line.strip('\n'))
        f.close()

    def _test_tooling(self):
        for e in ['openssl', 'certutil', 'pk12util']:
            if not find_executable(e):
                raise InsufficientTooling(e)

    def process(self):
        try:
            old = self._read_ldap_conf()
            new = self.convert(old)
            self._fix_ldap_conf(new)
        except (NotNSSConfiguration, AlreadyConverted) as e:
            return (None, e)
        except BaseException as e:
            return (False, e)
        return (True,)


def process(logger):
    try:
        ol = Openldap(logger)
    except BaseException as e:
        return (False, e)
    return ol.process()
