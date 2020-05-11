from leapp.libraries.actor import spamassassinconfigupdate
from leapp.libraries.common.spamassassinutils import SPAMC_CONFIG_FILE, SYSCONFIG_SPAMASSASSIN, SYSCONFIG_VARIABLE
from leapp.models.spamassassinfacts import SpamassassinFacts


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


def test_migrate_configs():
    facts = SpamassassinFacts(spamc_ssl_argument='sslv3',
                              spamd_ssl_version='sslv3',
                              service_overriden=False)
    fileops = MockFileOperations()
    fileops.files[SPAMC_CONFIG_FILE] = '--ssl sslv3\n# foo\n-B\n'
    content = ('# foo\n' +
               SYSCONFIG_VARIABLE + '="-c --ssl-version sslv3 -hdx"\n' +
               '# bar \n')
    fileops.files[SYSCONFIG_SPAMASSASSIN] = content
    backup_func = MockBackup()

    spamassassinconfigupdate.migrate_configs(facts, fileops, backup_func)

    assert backup_func.called == 2
    assert SPAMC_CONFIG_FILE in backup_func.paths
    assert SYSCONFIG_SPAMASSASSIN in backup_func.paths
    assert fileops.files[SPAMC_CONFIG_FILE] == '--ssl\n# foo\n-B\n'
    expected_content = ('# foo\n' +
                        SYSCONFIG_VARIABLE + '="-c --ssl -hx"\n' +
                        '# bar \n')
    assert fileops.files[SYSCONFIG_SPAMASSASSIN] == expected_content
