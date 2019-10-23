import os
import os.path as ph
import re
import subprocess as sp

from leapp.libraries.actor.utils import (
    copy_permissions,
    copy_some_permissions,
    NotNSSConfiguration,
    UMASK
)
from leapp.libraries.stdlib import run


class Nss(object):
    @staticmethod
    def _handle_popen_result(process, name):
        if process.returncode is None:
            raise RuntimeError('Process %s not finished yet!' % (name))
        if process.returncode != 0:
            stderr = process.stderr.read() if process.stderr else '<None>'
            raise RuntimeError('Running %s failed, the stderr was: %s' % (name, stderr))

    @staticmethod
    def _handle_run_result(process, name):
        if process['exit_code'] is None:
            raise RuntimeError('Process %s not finished yet!' % (name))
        if process['exit_code'] != 0:
            stderr = process['stderr'] if process['stderr'] else '<None>'
            raise RuntimeError('Running %s failed, the stderr was: %s' % (name, stderr))

    @classmethod
    def certutil_get_certs(cls, cacertdir):
        """Return list of certificates in NSS DB as {<name>: (<flags, ...>)}"""
        p = run(['certutil', '-d', cacertdir, '-L'], split=True, checked=False)
        if p['exit_code'] != 0:
            raise NotNSSConfiguration('Opening NSS database failed')
        lines = p['stdout'][4:]  # dropping header

        def parse_line(line):
            pattern = re.compile(r'(?P<name>.*?)\s+(?P<ssl>\w*),(?P<mime>\w*),(?P<mail>\w*)')
            matches = re.match(pattern, line)
            if matches:
                return (matches.group(1), matches.groups()[1:])
            return None

        parsed = {p[0]: p[1] for p in map(parse_line, lines) if p is not None}
        return parsed

    @classmethod
    def export_cert(cls, cacertdir, name, dest):
        try:
            old_umask = os.umask(UMASK)
            with open(dest, 'w') as fd:
                cmd = ['certutil', '-d', cacertdir, '-L', '-n', name, '-a']
                p = run(cmd, checked=False)
                fd.write(p['stdout'])
                cls._handle_run_result(p, 'certutil -L')
            copy_some_permissions(str(ph.join(cacertdir, 'cert%s.db')), [8, 9], dest)
        except BaseException as e:
            raise RuntimeError('Exporting certificate failed: ' + str(e))
        finally:
            os.umask(old_umask)

    @classmethod
    def export_key(cls, cacertdir, name, pinfile, dest):
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

                cls._handle_popen_result(pk12, 'pk12util')
                cls._handle_popen_result(ossl, 'openssl pkcs12')

                copy_some_permissions(str(ph.join(cacertdir, 'key%s.db')), [3, 4], dest)
            except BaseException as e:
                raise RuntimeError('Converting key to PEM format failed: ' + str(e))
            finally:
                os.umask(old_umask)

    @classmethod
    def export_ca_certs(cls, cacertdir, destdir):
        try:
            old_umask = os.umask(UMASK)
            os.mkdir(destdir)
            copy_permissions(cacertdir, destdir)
        except BaseException as e:
            raise RuntimeError('Could not create directory for extracted CA certificates: %s' % e)
        finally:
            os.umask(old_umask)

        certs = cls.certutil_get_certs(cacertdir)
        num = 0
        for name, flags in certs.items():
            if 'T' in flags[0]:
                filename = '{0:04d}.pem'.format(num)
                Nss.export_cert(cacertdir, name, ph.join(destdir, filename))
                num += 1
        try:
            run(['openssl', 'rehash', destdir])
        except BaseException as e:
            raise RuntimeError('Rehashing CA certificates failed: ' + str(e))
