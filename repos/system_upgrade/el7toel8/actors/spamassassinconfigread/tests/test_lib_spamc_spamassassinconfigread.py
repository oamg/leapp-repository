import errno

from leapp.libraries.actor import spamassassinconfigread_spamc
from leapp.libraries.common.testutils import make_IOError


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


def test_parse_spamc_ssl_argument():
    value = spamassassinconfigread_spamc._parse_spamc_ssl_argument('--ssl sslv3')
    assert value == 'sslv3'

    # equal sign format
    value = spamassassinconfigread_spamc._parse_spamc_ssl_argument('--ssl=tlsv1')
    assert value == 'tlsv1'


def test_parse_spamc_ssl_argument_without_valid_argument():
    # unknown argument
    value = spamassassinconfigread_spamc._parse_spamc_ssl_argument('--ssl foo')
    assert value is None

    # --ssl followed by another option
    value = spamassassinconfigread_spamc._parse_spamc_ssl_argument('--ssl -B')
    assert value is None

    # space surrounding the equal sign. This amounts to an unrecognized
    # argument (empty string)
    value = spamassassinconfigread_spamc._parse_spamc_ssl_argument('--ssl= tlsv1')
    assert value is None

    # space surrounding the equal sign. This amounts to an unrecognized
    # argument ("=tlsv1")
    value = spamassassinconfigread_spamc._parse_spamc_ssl_argument('--ssl =tlsv1')
    assert value is None


def test_parse_spamc_ssl_argument_multiline():
    value = spamassassinconfigread_spamc._parse_spamc_ssl_argument('-B --ssl \n sslv3 -c\n-H')
    assert value == 'sslv3'


def test_parse_spamc_ssl_argument_tls_supersedes_ssl():
    # Due to the way the spamc cmdline parser works, if '--ssl tlsv1' is
    # specified, all other --ssl options are effectively ignored and tlsv1 is
    # used.
    value = spamassassinconfigread_spamc._parse_spamc_ssl_argument('--ssl sslv3 --ssl tlsv1')
    assert value == 'tlsv1'

    # reverse order
    value = spamassassinconfigread_spamc._parse_spamc_ssl_argument('--ssl tlsv1 --ssl sslv3')
    assert value == 'tlsv1'


def test_parse_spamc_ssl_argument_comment():
    value = spamassassinconfigread_spamc._parse_spamc_ssl_argument('# --ssl tlsv1')
    assert value is None

    # comment mixed with actual option
    value = spamassassinconfigread_spamc._parse_spamc_ssl_argument('# --ssl tlsv1\n--ssl sslv3')
    assert value == 'sslv3'

    # comment mixed with actual option
    value = spamassassinconfigread_spamc._parse_spamc_ssl_argument('--ssl tlsv1\n# --ssl sslv3')
    assert value == 'tlsv1'


def test_parse_spamc_ssl_argument_crazy_corner_cases():
    # The option and value can have a comment in between
    value = spamassassinconfigread_spamc._parse_spamc_ssl_argument('--ssl\n# foo\ntlsv1')
    assert value == 'tlsv1'

    value = spamassassinconfigread_spamc._parse_spamc_ssl_argument('--ssl\n# foo\n# bar\nsslv3')
    assert value == 'sslv3'

    value = spamassassinconfigread_spamc._parse_spamc_ssl_argument('--ssl\n# foo\n# tlsv1\nsslv3')
    assert value == 'sslv3'


def test_get_spamc_ssl_argument():
    path = '/etc/mail/spamassassin/spamc.conf'
    fileops = MockFileOperations()
    fileops.files[path] = '--ssl sslv3'

    value = spamassassinconfigread_spamc.get_spamc_ssl_argument(fileops.read)

    assert fileops.files_read == {path: 1}
    assert value == 'sslv3'


def test_get_spamc_ssl_argument_empty():
    path = '/etc/mail/spamassassin/spamc.conf'
    fileops = MockFileOperations()
    fileops.files[path] = ''

    value = spamassassinconfigread_spamc.get_spamc_ssl_argument(fileops.read)

    assert fileops.files_read == {path: 1}
    assert value is None


def test_get_spamc_ssl_argument_nonexistent():
    path = '/etc/mail/spamassassin/spamc.conf'
    fileops = MockFileOperations()

    value = spamassassinconfigread_spamc.get_spamc_ssl_argument(fileops.read)

    assert fileops.files_read == {path: 1}
    assert value is None


def test_get_spamc_ssl_argument_inaccessible():
    path = '/etc/mail/spamassassin/spamc.conf'
    fileops = MockFileOperations(to_raise=make_IOError(errno.EACCES))

    value = spamassassinconfigread_spamc.get_spamc_ssl_argument(fileops.read)

    assert fileops.files_read == {path: 1}
    assert value is None
