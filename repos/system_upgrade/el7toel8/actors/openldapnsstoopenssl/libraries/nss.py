import os
import os.path as ph
import re
import subprocess as sp
import sys

from utils import (
    copy_permissions,
    copy_some_permissions,
    NotNSSConfiguration,
    UMASK
)


class Nss:
    @staticmethod
    def _handle_popen_result(process, name):
        if process.returncode == None:
            raise RuntimeError('Process %s not finished yet!' % (name))
        if process.returncode != 0:
            stderr = process.stderr.read() if process.stderr else '<None>'
            raise RuntimeError('Running %s failed, the stderr was: %s' % (name, stderr))

    @classmethod
    def certutil_get_certs(self, cacertdir):
        """Return list of certificates in NSS DB as {<name>: (<flags, ...>)}"""
        p = sp.Popen(['certutil', '-d', cacertdir, '-L'], stdout=sp.PIPE, stderr=sp.PIPE)
        stdout, _ = p.communicate()
        if p.returncode != 0:
            raise NotNSSConfiguration('Opening NSS database failed')
        lines = stdout.decode().split('\n')[4:]  # dropping header

        def parse_line(line):
            pattern = re.compile(r'(?P<name>.*?)\s+(?P<ssl>\w*),(?P<mime>\w*),(?P<mail>\w*)')
            matches = re.match(pattern, line)
            if matches:
                return (matches.group(1), matches.groups()[1:])
            else:
                return None

        parsed = {p[0]: p[1] for p in map(parse_line, lines) if p is not None}
        return parsed

    @classmethod
    def export_cert(self, cacertdir, name, dest):
        try:
            old_umask = os.umask(UMASK)
            with open(dest, 'w') as fd:
                cmd = ['certutil', '-d', cacertdir, '-L', '-n', name, '-a']
                p = sp.Popen(cmd, stdout=fd, stderr=sp.PIPE)
                p.wait()
                self._handle_popen_result(p, 'certutil -L')
            copy_some_permissions(str(ph.join(cacertdir, 'cert%s.db')), [8, 9], dest)
        except BaseException as e:
            raise RuntimeError('Exporting certificate failed: ' + str(e))
        finally:
            os.umask(old_umask)

    @classmethod
    def export_key(self, cacertdir, name, pinfile, dest):
        DUMMY = 'dummy'
        pass_arg = ['-K', ''] if pinfile is None else ['-k', pinfile]
        with open(os.devnull, 'w') as DEVNULL:
            try:
                pk12 = sp.Popen(['pk12util', '-d', cacertdir, '-o', '/dev/stdout',
                              '-n', name, '-W', DUMMY] + pass_arg,
                             stdout=sp.PIPE, stdin=DEVNULL, stderr=sp.PIPE)

                old_umask = os.umask(UMASK)
                ossl = sp.Popen(['openssl', 'pkcs12', '-in', '/dev/stdin', '-out', dest,
                              '-nodes', '-nocerts', '-passin', 'pass:{}'.format(DUMMY)],
                             stdin=sp.PIPE, stderr=sp.PIPE)
                ossl.communicate(input=pk12.stdout.read())

                ossl.wait()
                pk12.wait()

                self._handle_popen_result(pk12, 'pk12util')
                self._handle_popen_result(ossl, 'openssl pkcs12')

                copy_some_permissions(str(ph.join(cacertdir, 'key%s.db')), [3, 4], dest)
            except BaseException as e:
                raise RuntimeError('Converting key to PEM format failed: ' + str(e))
            finally:
                os.umask(old_umask)

    @classmethod
    def export_ca_certs(self, cacertdir, destdir):
        try:
            old_umask = os.umask(UMASK)
            os.mkdir(destdir)
            copy_permissions(cacertdir, destdir)
        except BaseException as e:
            raise RuntimeError('Could not create directory for extracted CA certificates: %s' % e)
        finally:
            os.umask(old_umask)

        certs = self.certutil_get_certs(cacertdir)
        num = 0
        for name, flags in certs.items():
            if 'T' in flags[0]:
                filename = '{0:04d}.pem'.format(num)
                Nss.export_cert(cacertdir, name, ph.join(destdir, filename))
                num += 1
        try:
            p = sp.Popen(['openssl', 'rehash', destdir],
                         stdout=sp.PIPE, stderr=sp.PIPE)
            p.wait()
        except BaseException as e:
            raise RuntimeError('Rehashing CA certificates failed: ' + str(e))
