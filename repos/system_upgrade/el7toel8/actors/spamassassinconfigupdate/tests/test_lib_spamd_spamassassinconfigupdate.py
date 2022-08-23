import errno

from leapp.libraries.actor import spamassassinconfigupdate_spamd
from leapp.libraries.common.spamassassinutils import SYSCONFIG_SPAMASSASSIN, SYSCONFIG_VARIABLE
from leapp.libraries.common.testutils import make_IOError, make_OSError
from leapp.models import SpamassassinFacts

# The tests for _drop_ssl_version and _drop_daemonize_option are overly
# restrictive in what output they accept - namely regarding whitespace and
# order of the options; don't be afraid to change the tests if they start
# failing due to whitespace or the order of options. It's done this way for
# simplicity - regular expressions accepting all acceptable outputs would be
# too complex.


def test_drop_ssl_version_double_quotes():
    value = '"--ssl --ssl-version tlsv1"'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == '"--ssl "'

    value = '"--ssl --ssl-version=tlsv1"'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == '"--ssl "'

    value = '"--ssl --ssl-version sslv3"'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == '"--ssl "'

    value = '"-d -c -m5 -H --ssl --ssl-version tlsv1"'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == '"-d -c -m5 -H --ssl "'

    value = '"-d -c -m5 -H --ssl --ssl-version sslv3"'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == '"-d -c -m5 -H --ssl "'

    value = '"-d --ssl -c -m5 --ssl-version tlsv1 -H"'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == '"-d --ssl -c -m5  -H"'

    value = '"-d --ssl -c -m5 --ssl-version sslv3 -H"'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == '"-d --ssl -c -m5  -H"'

    value = '"-d --ssl -c -m5 --ssl-version=sslv3 -H"'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == '"-d --ssl -c -m5  -H"'


def test_drop_ssl_version_no_quotes():
    value = '-d --ssl -c -m5 --ssl-version sslv3 -H'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == '-d --ssl -c -m5  -H'

    value = '-d --ssl -c -m5 --ssl-version=sslv3 -H'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == '-d --ssl -c -m5  -H'


def test_drop_ssl_version_single_quotes():
    value = "'-d --ssl -c -m5 --ssl-version sslv3 -H'"
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == "'-d --ssl -c -m5  -H'"

    value = "'-d --ssl -c -m5 --ssl-version=sslv3 -H'"
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == "'-d --ssl -c -m5  -H'"


def test_drop_ssl_version_ssl_version_implies_ssl():
    # If --ssl-version is used and --ssl is missing, we need to add --ssl
    # because --ssl-version implies --ssl
    value = '--ssl-version tlsv1'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == '--ssl'

    value = '--ssl-version=tlsv1'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == '--ssl'

    value = '"--ssl-version tlsv1"'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == '"--ssl"'

    value = ' --ssl-version tlsv1 '
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == ' --ssl '

    value = '-d -c -m5 --ssl-version sslv3 -H'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == '-d -c -m5 --ssl -H'

    value = '-d -c -m5 --ssl-version=sslv3 -H'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == '-d -c -m5 --ssl -H'

    value = '-d -c -m5 -H --ssl-version sslv3'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == '-d -c -m5 -H --ssl'


def test_drop_ssl_version_invalid_argument():
    # If the argument of --ssl-version is invalid, we don't touch it because
    # the configuration is invalid and the user needs to fix it up anyway.
    value = '--ssl-version foo'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == value

    value = '--ssl-version=foo'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == value

    value = '-d --ssl -c --ssl-version foo -H'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == value

    value = '-d --ssl -c --ssl-version=foo -H'
    rewritten = spamassassinconfigupdate_spamd._drop_ssl_version(value)
    assert rewritten == value


def test_drop_daemonize_option_double_quotes():
    value = '"-d -c -m5 -H"'
    rewritten = spamassassinconfigupdate_spamd._drop_daemonize_option(value)
    assert rewritten == '" -c -m5 -H"'

    value = '"-c -d -m5 -H"'
    rewritten = spamassassinconfigupdate_spamd._drop_daemonize_option(value)
    assert rewritten == '"-c  -m5 -H"'


def test_drop_daemonize_option_no_quotes():
    value = '-d -c -m5 -H'
    rewritten = spamassassinconfigupdate_spamd._drop_daemonize_option(value)
    assert rewritten == ' -c -m5 -H'

    value = '-c -d -m5 -H'
    rewritten = spamassassinconfigupdate_spamd._drop_daemonize_option(value)
    assert rewritten == '-c  -m5 -H'


def test_drop_daemonize_option_single_quotes():
    value = "'-d -c -m5 -H'"
    rewritten = spamassassinconfigupdate_spamd._drop_daemonize_option(value)
    assert rewritten == "' -c -m5 -H'"

    value = "'-c -d -m5 -H'"
    rewritten = spamassassinconfigupdate_spamd._drop_daemonize_option(value)
    assert rewritten == "'-c  -m5 -H'"


def test_drop_daemonize_option_longopt():
    value = '--daemonize -c -m5 -H'
    rewritten = spamassassinconfigupdate_spamd._drop_daemonize_option(value)
    assert rewritten == ' -c -m5 -H'

    value = '-c --daemonize -m5 -H'
    rewritten = spamassassinconfigupdate_spamd._drop_daemonize_option(value)
    assert rewritten == '-c  -m5 -H'


def test_drop_daemonize_short_form():
    value = '-cdL -m5'
    rewritten = spamassassinconfigupdate_spamd._drop_daemonize_option(value)
    assert rewritten == '-cL -m5'

    value = '-dcL -m5'
    rewritten = spamassassinconfigupdate_spamd._drop_daemonize_option(value)
    assert rewritten == '-cL -m5'

    value = '-cLd -m5'
    rewritten = spamassassinconfigupdate_spamd._drop_daemonize_option(value)
    assert rewritten == '-cL -m5'


def test_drop_daemonize_option_repeated():
    value = '--daemonize -cdd -m5 -dcd --daemonize -H -ddd'
    rewritten = spamassassinconfigupdate_spamd._drop_daemonize_option(value)
    assert rewritten == ' -c -m5 -c  -H '


def test_rewrite_spamd_option_no_assignment():
    content = '# foo\nbar=foobar\n'
    ops = [spamassassinconfigupdate_spamd._drop_ssl_version, spamassassinconfigupdate_spamd._drop_daemonize_option]
    rewritten = spamassassinconfigupdate_spamd._rewrite_spamd_option(content, ops)
    assert rewritten == content


def test_rewrite_spamd_option_comments():
    ops = [spamassassinconfigupdate_spamd._drop_ssl_version, spamassassinconfigupdate_spamd._drop_daemonize_option]

    # Leave comments be
    content = '# foo\n# bar\nSPAMDOPTIONS="--ssl-version tlsv1 -d --ssl"\n# foobar\n'
    rewritten = spamassassinconfigupdate_spamd._rewrite_spamd_option(content, ops)
    assert rewritten == '# foo\n# bar\nSPAMDOPTIONS="  --ssl"\n# foobar\n'

    content = '# foo\n# bar\n# SPAMDOPTIONS="--ssl-version tlsv1 -d --ssl"\n# foobar\n'
    rewritten = spamassassinconfigupdate_spamd._rewrite_spamd_option(content, ops)
    assert rewritten == content

    content = '# foo\\\n' \
              'SPAMDOPTIONS="--ssl-version tlsv1 -d --ssl"\n'  # still a comment
    rewritten = spamassassinconfigupdate_spamd._rewrite_spamd_option(content, ops)
    assert rewritten == content


def test_rewrite_spamd_option_last_assignment_takes_effect():
    ops = [spamassassinconfigupdate_spamd._drop_ssl_version, spamassassinconfigupdate_spamd._drop_daemonize_option]

    # Only the last assignment to a variable takes effect, so that's the only
    # assignment that we need to take care of
    content = 'SPAMDOPTIONS="-c -d"\n' \
              'SPAMDOPTIONS="-c -d -H"\n'
    rewritten = spamassassinconfigupdate_spamd._rewrite_spamd_option(content, ops)
    assert rewritten == '%s\nSPAMDOPTIONS="-c  -H"\n' % content.split('\n')[0]

    content = 'SPAMDOPTIONS="--ssl-version tlsv1 --ssl"\n' \
              'SPAMDOPTIONS="-c --ssl --ssl-version sslv3 -H"\n'
    rewritten = spamassassinconfigupdate_spamd._rewrite_spamd_option(content, ops)
    assert rewritten == '%s\nSPAMDOPTIONS="-c --ssl  -H"\n' % content.split('\n')[0]


def test_rewrite_spamd_option_multiline_value():
    ops = [spamassassinconfigupdate_spamd._drop_ssl_version, spamassassinconfigupdate_spamd._drop_daemonize_option]
    content = 'SPAMDOPTIONS="--ssl \\\n--ssl-version sslv3"\n'
    rewritten = spamassassinconfigupdate_spamd._rewrite_spamd_option(content, ops)
    assert rewritten == 'SPAMDOPTIONS="--ssl "\n'


def test_rewrite_spamd_config():
    facts = SpamassassinFacts(spamd_ssl_version='tlsv1', service_overriden=False)
    content = '# Options passed to spamd\n' \
              'SPAMDOPTIONS="-c -d -m5 --ssl -H --ssl-version tlsv1"\n'

    rewritten = spamassassinconfigupdate_spamd._rewrite_spamd_config(facts, content)

    assert rewritten == '# Options passed to spamd\n' \
                        'SPAMDOPTIONS="-c  -m5 --ssl -H "\n'


def test_rewrite_spamd_config_service_overriden():
    # If the service is overridden, the service type (simple/forking) remains
    # the same after upgrade. So we must not remove the -d option.
    facts = SpamassassinFacts(spamd_ssl_version='sslv3', service_overriden=True)
    content = '# Options to spamd\n' \
              'SPAMDOPTIONS="-c -d -m5 --ssl -H --ssl-version sslv3"\n'

    rewritten = spamassassinconfigupdate_spamd._rewrite_spamd_config(facts, content)

    assert rewritten == '# Options to spamd\n' \
                        'SPAMDOPTIONS="-c -d -m5 --ssl -H "\n'


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


def test_migrate_spamd_config():
    facts = SpamassassinFacts(service_overriden=False, spamd_ssl_version='tlsv1')
    fileops = MockFileOperations()
    content = ('# foo\n' +
               SYSCONFIG_VARIABLE + '="-c --ssl-version tlsv1 -hdx"\n' +
               '# bar \n')
    fileops.files[SYSCONFIG_SPAMASSASSIN] = content
    backup_func = MockBackup()

    spamassassinconfigupdate_spamd.migrate_spamd_config(facts, fileops, backup_func)

    assert backup_func.called == 1
    assert backup_func.paths[0] == SYSCONFIG_SPAMASSASSIN
    expected_content = ('# foo\n' +
                        SYSCONFIG_VARIABLE + '="-c --ssl -hx"\n' +
                        '# bar \n')
    assert fileops.files[SYSCONFIG_SPAMASSASSIN] == expected_content
    assert fileops.read_called == 1
    assert fileops.files_read[SYSCONFIG_SPAMASSASSIN] == 1
    assert fileops.write_called == 1
    assert fileops.files_written[SYSCONFIG_SPAMASSASSIN] == 1


def test_migrate_spamd_config_nothing_to_migrate():
    facts = SpamassassinFacts(service_overriden=True, spamd_ssl_version=None)
    fileops = MockFileOperations()
    content = ('# foo\n' +
               SYSCONFIG_VARIABLE + '="-c -hdx"\n' +
               '# bar \n')
    fileops.files[SYSCONFIG_SPAMASSASSIN] = content
    backup_func = MockBackup()

    spamassassinconfigupdate_spamd.migrate_spamd_config(facts, fileops, backup_func)

    assert fileops.read_called == 0
    assert fileops.write_called == 0
    assert backup_func.called == 0


def test_migrate_spamd_config_no_write_if_backup_fails():
    # OSError (e.g. os.open)
    facts = SpamassassinFacts(service_overriden=False, spamd_ssl_version='tlsv1')
    fileops = MockFileOperations()
    content = ('# foo\n' +
               SYSCONFIG_VARIABLE + '="-c --ssl-version tlsv1 -hdx"\n' +
               '# bar \n')
    fileops.files[SYSCONFIG_SPAMASSASSIN] = content
    backup_func = MockBackup(to_raise=make_OSError(errno.EACCES))

    spamassassinconfigupdate_spamd.migrate_spamd_config(facts, fileops, backup_func)

    assert backup_func.called == 1
    assert fileops.write_called == 0

    # IOError (e.g. file.read)
    facts = SpamassassinFacts(service_overriden=False, spamd_ssl_version='tlsv1')
    fileops = MockFileOperations()
    content = ('# foo\n' +
               SYSCONFIG_VARIABLE + '="-c --ssl-version tlsv1 -hdx"\n' +
               '# bar \n')
    fileops.files[SYSCONFIG_SPAMASSASSIN] = content
    backup_func = MockBackup(to_raise=make_IOError(errno.EACCES))

    spamassassinconfigupdate_spamd.migrate_spamd_config(facts, fileops, backup_func)

    assert backup_func.called == 1
    assert fileops.write_called == 0


def test_migrate_spamd_config_read_failure():
    # OSError (e.g. os.open)
    facts = SpamassassinFacts(service_overriden=False, spamd_ssl_version='tlsv1')
    fileops = MockFileOperations(read_error=make_OSError(errno.EACCES))
    content = ('# foo\n' +
               SYSCONFIG_VARIABLE + '="-c --ssl-version tlsv1 -hdx"\n' +
               '# bar \n')
    fileops.files[SYSCONFIG_SPAMASSASSIN] = content
    backup_func = MockBackup()

    spamassassinconfigupdate_spamd.migrate_spamd_config(facts, fileops, backup_func)

    # The main purpose of this test is to check that exceptions are handled
    # properly. The following assertions are supplementary.
    assert fileops.read_called == 1
    assert fileops.write_called == 0

    # IOError (e.g. builtin open)
    facts = SpamassassinFacts(service_overriden=False, spamd_ssl_version='tlsv1')
    fileops = MockFileOperations(read_error=make_IOError(errno.EACCES))
    content = ('# foo\n' +
               SYSCONFIG_VARIABLE + '="-c --ssl-version tlsv1 -hdx"\n' +
               '# bar \n')
    fileops.files[SYSCONFIG_SPAMASSASSIN] = content
    backup_func = MockBackup()

    spamassassinconfigupdate_spamd.migrate_spamd_config(facts, fileops, backup_func)

    assert fileops.read_called == 1
    assert fileops.write_called == 0


def test_migrate_spamd_config_write_failure():
    # OSError (e.g. os.open)
    facts = SpamassassinFacts(service_overriden=False, spamd_ssl_version='tlsv1')
    fileops = MockFileOperations(write_error=make_OSError(errno.EACCES))
    content = ('# foo\n' +
               SYSCONFIG_VARIABLE + '="-c --ssl-version tlsv1 -hdx"\n' +
               '# bar \n')
    fileops.files[SYSCONFIG_SPAMASSASSIN] = content
    backup_func = MockBackup()

    spamassassinconfigupdate_spamd.migrate_spamd_config(facts, fileops, backup_func)

    # The main purpose of this test is to check that exceptions are handled
    # properly. The following assertions are supplementary.
    assert fileops.read_called == 1
    assert fileops.write_called == 1

    # IOError (e.g. builtin open)
    facts = SpamassassinFacts(service_overriden=False, spamd_ssl_version='tlsv1')
    fileops = MockFileOperations(write_error=make_IOError(errno.EACCES))
    content = ('# foo\n' +
               SYSCONFIG_VARIABLE + '="-c --ssl-version tlsv1 -hdx"\n' +
               '# bar \n')
    fileops.files[SYSCONFIG_SPAMASSASSIN] = content
    backup_func = MockBackup()

    spamassassinconfigupdate_spamd.migrate_spamd_config(facts, fileops, backup_func)

    assert fileops.read_called == 1
    assert fileops.write_called == 1


def test_migrate_spamd_config_no_writes_with_unmodified_config():
    # Test that no writes are performed if the sysconfig file is in its
    # default state and thus gets replaced during the RPM upgrade.
    facts = SpamassassinFacts(service_overriden=False, spamd_ssl_version='tlsv1')
    # Content of the sysconfig file from RHEL-8
    content = ('# Options to spamd\n'
               'SPAMDOPTIONS="-c -m5 -H --razor-home-dir=\'/var/lib/razor/\' --razor-log-file=\'sys-syslog\'"\n')
    fileops = MockFileOperations()
    fileops.files[SYSCONFIG_SPAMASSASSIN] = content
    backup_func = MockBackup()

    spamassassinconfigupdate_spamd.migrate_spamd_config(facts, fileops, backup_func)

    assert backup_func.called == 0
    assert fileops.read_called == 1
    assert fileops.write_called == 0
