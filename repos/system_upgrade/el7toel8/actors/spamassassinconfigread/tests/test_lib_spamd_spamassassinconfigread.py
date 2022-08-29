import errno
import os

from leapp.libraries.actor import spamassassinconfigread_spamd
from leapp.libraries.common.testutils import make_IOError, make_OSError


class MockFileOperations(object):
    def __init__(self, to_raise=None):
        self.files = {}
        self.files_read = {}
        self.read_called = 0
        self.to_raise = to_raise

    def _increment_read_counters(self, path):
        self.read_called += 1
        self.files_read.setdefault(path, 0)
        self.files_read[path] += 1

    def read(self, path):
        self._increment_read_counters(path)
        if self.to_raise is not None:
            raise self.to_raise
        try:
            return self.files[path]
        except KeyError:
            raise make_IOError(errno.ENOENT)


class MockListDir(object):
    def __init__(self, path=None, file_names=None, to_raise=None):
        self.path = None if path is None else os.path.normpath(path)
        self.file_names = file_names
        self.to_raise = to_raise
        self.error = False

    def listdir(self, path):
        if self.to_raise:
            raise self.to_raise
        if os.path.normpath(path) == self.path:
            return self.file_names
        self.error = True
        raise make_OSError(errno.ENOENT)


def test_spamassassin_service_overriden():
    listdir = MockListDir(path='/etc/systemd/system', file_names=['spamassassin.service'])
    overridden = spamassassinconfigread_spamd.spamassassin_service_overriden(listdir.listdir)
    assert overridden is True

    listdir = MockListDir(path='/etc/systemd/system',
                          file_names=['foo.service', 'spamassassin.service', 'bar.service'])
    overridden = spamassassinconfigread_spamd.spamassassin_service_overriden(listdir.listdir)
    assert overridden is True
    assert not listdir.error


def test_spamassassin_service_overriden_nonexistent():
    listdir = MockListDir(path='/etc/systemd/system', file_names=[])
    overridden = spamassassinconfigread_spamd.spamassassin_service_overriden(listdir.listdir)
    assert overridden is False

    listdir = MockListDir(path='/etc/systemd/system',
                          file_names=['foo.service', 'bar.service'])
    overridden = spamassassinconfigread_spamd.spamassassin_service_overriden(listdir.listdir)
    assert overridden is False
    assert not listdir.error


def test_spamassassin_service_overriden_nonexistent_dir():
    listdir = MockListDir(to_raise=make_OSError(errno.ENOENT))
    overridden = spamassassinconfigread_spamd.spamassassin_service_overriden(listdir.listdir)
    assert overridden is False


def test_spamassassin_service_overriden_nonexistent_inaccessible():
    # If we can't check if the file is there, we treat it as if it was there,
    # so that the SpamassassinConfigUpdate actor doesn't make changes to
    # /etc/sysconfig/spamassassin that may not be justified.
    listdir = MockListDir(to_raise=make_OSError(errno.EACCES))
    overridden = spamassassinconfigread_spamd.spamassassin_service_overriden(listdir.listdir)
    assert overridden is True


def test_parse_ssl_version_sslv3():
    content = 'SPAMDOPTIONS="--ssl-version sslv3"'
    value = spamassassinconfigread_spamd._parse_ssl_version(content)
    assert value == 'sslv3'

    content = 'SPAMDOPTIONS="-cd -m5 --ssl-version sslv3 -H"'
    value = spamassassinconfigread_spamd._parse_ssl_version(content)
    assert value == 'sslv3'


def test_parse_ssl_version_tlsv1():
    content = 'SPAMDOPTIONS="--ssl-version tlsv1"'
    value = spamassassinconfigread_spamd._parse_ssl_version(content)
    assert value == 'tlsv1'

    content = 'SPAMDOPTIONS="-cd -m5 --ssl-version tlsv1 -H"'
    value = spamassassinconfigread_spamd._parse_ssl_version(content)
    assert value == 'tlsv1'


def test_parse_ssl_version_invalid_argument():
    # If an invalid argument is used, we treat it as if the option was not
    # specified at all, so that the config update actor doesn't touch it. We
    # don't want to break the config even more.
    content = 'SPAMDOPTIONS="--ssl-version foo"\n'
    value = spamassassinconfigread_spamd._parse_ssl_version(content)
    assert value is None


def test_parse_ssl_version_comments():
    content = '# foo\nSPAMDOPTIONS="--ssl-version tlsv1"\n# bar\n'
    value = spamassassinconfigread_spamd._parse_ssl_version(content)
    assert value == 'tlsv1'


def test_parse_ssl_version_repeated():
    # The last --ssl-version option takes effect
    content = 'SPAMDOPTIONS="--ssl-version tlsv1 --ssl-version sslv3"\n'
    value = spamassassinconfigread_spamd._parse_ssl_version(content)
    assert value == 'sslv3'

    content = 'SPAMDOPTIONS="--ssl-version sslv3 --ssl-version tlsv1"\n'
    value = spamassassinconfigread_spamd._parse_ssl_version(content)
    assert value == 'sslv3'


def test_parse_ssl_version_last_assignment_takes_effect():
    # The last assignment to SPAMDOPTIONS takes effect
    content = 'SPAMDOPTIONS="--ssl-version tlsv1"\nSPAMDOPTIONS="--ssl-version sslv3"\n'
    value = spamassassinconfigread_spamd._parse_ssl_version(content)
    assert value == 'sslv3'


def test_parse_ssl_version_multiline():
    content = 'SPAMDOPTIONS="--ssl \\\n --ssl-version tlsv1"\n'
    value = spamassassinconfigread_spamd._parse_ssl_version(content)
    assert value == 'tlsv1'

    content = 'SPAMDOPTIONS="--ssl-version \\\n sslv3"\n'
    value = spamassassinconfigread_spamd._parse_ssl_version(content)
    assert value == 'sslv3'


def test_parse_ssl_version_multiline_comment():
    content = ('SPAMDOPTIONS="--ssl-version tlsv1"\n'
               '# foo \\\nSPAMDOPTIONS="--ssl-version sslv3" \\\n still a comment')
    value = spamassassinconfigread_spamd._parse_ssl_version(content)
    assert value == 'tlsv1'


def test_get_spamd_ssl_version():
    path = '/etc/sysconfig/spamassassin'
    fileops = MockFileOperations()
    fileops.files[path] = '# foo\nSPAMDOPTIONS="--ssl-version tlsv1"\n# bar\n'

    value = spamassassinconfigread_spamd.get_spamd_ssl_version(fileops.read)

    assert value == 'tlsv1'


def test_get_spamd_ssl_version_nonexistent():
    fileops = MockFileOperations()
    value = spamassassinconfigread_spamd.get_spamd_ssl_version(fileops.read)
    assert value is None


def test_get_spamd_ssl_version_inaccessible():
    fileops = MockFileOperations(to_raise=make_IOError(errno.EACCES))
    value = spamassassinconfigread_spamd.get_spamd_ssl_version(fileops.read)
    assert value is None
