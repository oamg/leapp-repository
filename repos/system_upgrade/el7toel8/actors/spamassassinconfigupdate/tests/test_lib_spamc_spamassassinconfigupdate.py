import errno

from leapp.libraries.actor import spamassassinconfigupdate_spamc
from leapp.libraries.common.spamassassinutils import SPAMC_CONFIG_FILE
from leapp.libraries.common.testutils import make_IOError, make_OSError
from leapp.models.spamassassinfacts import SpamassassinFacts

# The test cases reuse values from the SpamassassinConfigRead test cases


def test_rewrite_spamc_config():
    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('--ssl sslv3\n')
    assert new_content == '--ssl\n'

    # equal sign format
    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('--ssl=tlsv1\n')
    assert new_content == '--ssl\n'

    # no argument
    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('--ssl\n')
    assert new_content == '--ssl\n'


def test_rewrite_spamc_config_without_valid_argument():
    # If we encounter an unrecognized parameter, we leave it be - the
    # configuration is invalid anyway, so let's not mess it up even more.
    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('--ssl foo\n')
    assert new_content == '--ssl foo\n'

    # --ssl followed by another option
    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('--ssl -B\n')
    assert new_content == '--ssl -B\n'

    # space surrounding the equal sign. This amounts to an unrecognized
    # argument (empty string)
    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('--ssl= tlsv1\n')
    assert new_content == '--ssl= tlsv1\n'

    # space surrounding the equal sign. This amounts to an unrecognized
    # argument ("=tlsv1")
    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('--ssl =tlsv1\n')
    assert new_content == '--ssl =tlsv1\n'


def test_rewrite_spamc_config_multiline():
    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('-B --ssl \n sslv3 -c\n-H\n')
    assert new_content == '-B --ssl \n -c\n-H\n'

    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('--ssl\n-B\n')
    assert new_content == '--ssl\n-B\n'


def test_rewrite_spamc_config_tls_supersedes_ssl():
    # Ideally, the result would be a single '--ssl' option. However for
    # simplicity, we allow the option to be output twice. It's not nice, but
    # there's nothing technically wrong with it. And it's really a corner case
    # anyway.  If someone fixes it, this test case can be updated to expect
    # '--ssl' as output.
    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('--ssl sslv3 --ssl tlsv1\n')
    assert new_content == '--ssl --ssl\n'

    # reverse order
    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('--ssl tlsv1 --ssl sslv3\n')
    assert new_content == '--ssl --ssl\n'


def test_rewrite_spamc_config_comment():
    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('# --ssl tlsv1\n')
    assert new_content == '# --ssl tlsv1\n'

    # comment mixed with actual option
    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('# --ssl tlsv1\n--ssl sslv3\n')
    assert new_content == '# --ssl tlsv1\n--ssl\n'

    # comment mixed with actual option
    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('--ssl tlsv1\n# --ssl sslv3\n')
    assert new_content == '--ssl\n# --ssl sslv3\n'


def test_rewrite_spamc_config_crazy_corner_cases():
    # The option and new_content can have a comment in between
    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('--ssl\n# foo\ntlsv1\n')
    assert new_content == '--ssl\n# foo\n\n'

    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('--ssl\n# foo\n# bar\nsslv3\n')
    assert new_content == '--ssl\n# foo\n# bar\n\n'

    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('--ssl\n# foo\n# tlsv1\nsslv3\n')
    assert new_content == '--ssl\n# foo\n# tlsv1\n\n'

    # --ssl followed by another option
    new_content = spamassassinconfigupdate_spamc._rewrite_spamc_config('--ssl\n# foo\n-B\n')
    assert new_content == '--ssl\n# foo\n-B\n'


class MockBackup(object):
    def __init__(self, to_raise=None):
        self.to_raise = to_raise
        self.called = 0
        self.paths = []

    def __call__(self, path):
        self.called += 1
        self.paths.append(path)
        if self.to_raise:
            raise self.to_raise
        return '/path/to/backup'


class MockFileOperations(object):
    def __init__(self, read_error=None, write_error=None):
        self.files = {}
        self.files_read = {}
        self.files_written = {}
        self.read_called = 0
        self.write_called = 0
        self.read_error = read_error
        self.write_error = write_error

    def _increment_read_counters(self, path):
        self.read_called += 1
        self.files_read.setdefault(path, 0)
        self.files_read[path] += 1

    def read(self, path):
        self._increment_read_counters(path)
        if self.read_error:
            raise self.read_error
        return self.files[path]

    def _increment_write_counters(self, path):
        self.write_called += 1
        self.files_written.setdefault(path, 0)
        self.files_written[path] += 1

    def write(self, path, content):
        self._increment_write_counters(path)
        if self.write_error:
            raise self.write_error
        self.files[path] = content


def test_migrate_spamc_config():
    facts = SpamassassinFacts(spamc_ssl_argument='sslv3', service_overriden=False)
    fileops = MockFileOperations()
    fileops.files[SPAMC_CONFIG_FILE] = '--ssl sslv3\n# foo\n-B\n'
    backup_func = MockBackup()

    spamassassinconfigupdate_spamc.migrate_spamc_config(facts, fileops, backup_func)

    assert backup_func.called == 1
    assert backup_func.paths[0] == SPAMC_CONFIG_FILE
    assert fileops.files[SPAMC_CONFIG_FILE] == '--ssl\n# foo\n-B\n'
    assert fileops.read_called == 1
    assert fileops.files_read[SPAMC_CONFIG_FILE] == 1
    assert fileops.write_called == 1
    assert fileops.files_written[SPAMC_CONFIG_FILE] == 1


def test_migrate_spamc_config_no_ssl_option():
    facts = SpamassassinFacts(spamc_ssl_argument=None, service_overriden=False)
    fileops = MockFileOperations()
    backup_func = MockBackup()

    spamassassinconfigupdate_spamc.migrate_spamc_config(facts, fileops, backup_func)

    assert backup_func.called == 0
    assert fileops.read_called == 0
    assert fileops.write_called == 0


def test_migrate_spamc_config_no_write_if_backup_fails():
    # OSError (e.g. os.open)
    facts = SpamassassinFacts(spamc_ssl_argument='sslv3', service_overriden=False)
    fileops = MockFileOperations()
    backup_func = MockBackup(to_raise=make_OSError(errno.EACCES))

    spamassassinconfigupdate_spamc.migrate_spamc_config(facts, fileops, backup_func)

    assert fileops.write_called == 0

    # IOError (e.g. file.read)
    facts = SpamassassinFacts(spamc_ssl_argument='sslv3', service_overriden=False)
    fileops = MockFileOperations()
    backup_func = MockBackup(to_raise=make_IOError(errno.EACCES))

    spamassassinconfigupdate_spamc.migrate_spamc_config(facts, fileops, backup_func)

    assert fileops.write_called == 0


def test_migrate_spamc_config_read_failure():
    # OSError (e.g. os.open)
    facts = SpamassassinFacts(spamc_ssl_argument='sslv3', service_overriden=False)
    fileops = MockFileOperations(read_error=make_OSError(errno.EACCES))
    backup_func = MockBackup()

    spamassassinconfigupdate_spamc.migrate_spamc_config(facts, fileops, backup_func)

    # The main purpose of this test is to check that exceptions are handled
    # properly. The following assertions are supplementary.
    assert fileops.read_called == 1
    assert fileops.write_called == 0

    # IOError (e.g. builtin open)
    facts = SpamassassinFacts(spamc_ssl_argument='sslv3', service_overriden=False)
    fileops = MockFileOperations(read_error=make_IOError(errno.EACCES))
    backup_func = MockBackup()

    spamassassinconfigupdate_spamc.migrate_spamc_config(facts, fileops, backup_func)

    assert fileops.read_called == 1
    assert fileops.write_called == 0


def test_migrate_spamc_config_write_failure():
    # OSError (e.g. os.open)
    facts = SpamassassinFacts(spamc_ssl_argument='sslv3', service_overriden=False)
    fileops = MockFileOperations(write_error=make_OSError(errno.EACCES))
    fileops.files[SPAMC_CONFIG_FILE] = '--ssl sslv3\n# foo\n-B\n'
    backup_func = MockBackup()

    spamassassinconfigupdate_spamc.migrate_spamc_config(facts, fileops, backup_func)

    # The main purpose of this test is to check that exceptions are handled
    # properly. The following assertions are supplementary.
    assert fileops.read_called == 1
    assert fileops.write_called == 1

    # IOError (e.g. builtin open)
    facts = SpamassassinFacts(spamc_ssl_argument='sslv3', service_overriden=False)
    fileops = MockFileOperations(write_error=make_IOError(errno.EACCES))
    fileops.files[SPAMC_CONFIG_FILE] = '--ssl sslv3\n# foo\n-B\n'
    backup_func = MockBackup()

    spamassassinconfigupdate_spamc.migrate_spamc_config(facts, fileops, backup_func)

    assert fileops.read_called == 1
    assert fileops.write_called == 1
