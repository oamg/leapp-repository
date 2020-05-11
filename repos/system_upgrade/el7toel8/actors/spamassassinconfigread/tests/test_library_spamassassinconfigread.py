import errno
import os

from leapp.libraries.actor import spamassassinconfigread
from leapp.libraries.common.testutils import make_IOError, make_OSError


class MockFileOperations(object):
    def __init__(self):
        self.files = {}
        self.files_read = {}
        self.read_called = 0

    def _increment_read_counters(self, path):
        self.read_called += 1
        self.files_read.setdefault(path, 0)
        self.files_read[path] += 1

    def read(self, path):
        self._increment_read_counters(path)
        try:
            return self.files[path]
        except KeyError:
            raise make_IOError(errno.ENOENT)


class MockListDir(object):
    def __init__(self, path=None, file_names=None):
        self.path = None if path is None else os.path.normpath(path)
        self.file_names = file_names
        self.error = False

    def listdir(self, path):
        if os.path.normpath(path) == self.path:
            return self.file_names
        self.error = True
        raise make_OSError(errno.ENOENT)


def test_get_spamassassin_facts():
    spamc_path = '/etc/mail/spamassassin/spamc.conf'
    spamd_path = '/etc/sysconfig/spamassassin'
    fileops = MockFileOperations()
    fileops.files[spamc_path] = '--ssl sslv3'
    fileops.files[spamd_path] = 'SPAMDOPTIONS="--ssl-version tlsv1"'
    listdir = MockListDir(path='/etc/systemd/system', file_names=['spamassassin.service'])

    facts = spamassassinconfigread.get_spamassassin_facts(read_func=fileops.read, listdir=listdir.listdir)

    assert len(fileops.files_read) == 2
    assert spamc_path in fileops.files_read
    assert spamd_path in fileops.files_read
    assert facts.spamc_ssl_argument == 'sslv3'
    assert facts.spamd_ssl_version == 'tlsv1'
    assert facts.service_overriden is True
    assert not listdir.error


def test_get_spamassassin_facts_nonexistent_config():
    spamc_path = '/etc/mail/spamassassin/spamc.conf'
    spamd_path = '/etc/sysconfig/spamassassin'
    fileops = MockFileOperations()
    listdir = MockListDir(path='/etc/systemd/system', file_names=[])

    facts = spamassassinconfigread.get_spamassassin_facts(read_func=fileops.read, listdir=listdir.listdir)

    assert len(fileops.files_read) == 2
    assert spamc_path in fileops.files_read
    assert spamd_path in fileops.files_read
    assert facts.spamc_ssl_argument is None
    assert facts.spamd_ssl_version is None
    assert facts.service_overriden is False
    assert not listdir.error
