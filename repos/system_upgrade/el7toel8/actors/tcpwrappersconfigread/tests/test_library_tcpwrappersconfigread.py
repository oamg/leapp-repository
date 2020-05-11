import errno

from leapp.libraries.actor import tcpwrappersconfigread
from leapp.libraries.common.testutils import make_IOError


class MockFileReader(object):
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


def test_get_daemon_list_in_line_simple():
    line = 'vsftpd : 192.168.2.*'
    daemon_list = tcpwrappersconfigread._get_daemon_list_in_line(line)
    assert daemon_list.value == ['vsftpd']


def test_get_daemon_list_in_line_multiple():
    line = 'vsftpd, sendmail : 192.168.2.*'
    daemon_list = tcpwrappersconfigread._get_daemon_list_in_line(line)
    assert daemon_list.value == ['vsftpd', 'sendmail']

    line = 'ALL EXCEPT sendmail : 192.168.2.*'
    daemon_list = tcpwrappersconfigread._get_daemon_list_in_line(line)
    assert daemon_list.value == ['ALL', 'EXCEPT', 'sendmail']

    # different separators
    line = 'vsftpd,sendmail : 192.168.2.*'
    daemon_list = tcpwrappersconfigread._get_daemon_list_in_line(line)
    assert daemon_list.value == ['vsftpd', 'sendmail']

    line = 'vsftpd\tsendmail : 192.168.2.*'
    daemon_list = tcpwrappersconfigread._get_daemon_list_in_line(line)
    assert daemon_list.value == ['vsftpd', 'sendmail']

    line = 'vsftpd, \t sendmail : 192.168.2.*'
    daemon_list = tcpwrappersconfigread._get_daemon_list_in_line(line)
    assert daemon_list.value == ['vsftpd', 'sendmail']


def test_get_daemon_list_in_line_malformed():
    line = 'foo'
    daemon_list = tcpwrappersconfigread._get_daemon_list_in_line(line)
    # tcp_wrappers actually ignores lines like this, but there's no harm in being
    # over-sensitive here.
    assert daemon_list.value == ['foo']


def test_get_lines_empty():
    content = ''
    lines = tcpwrappersconfigread._get_lines(content)
    assert lines == ['']


def test_get_lines_simple():
    content = 'vsftpd : 192.168.2.*\n' \
              'ALL : 192.168.1.*\n'
    lines = tcpwrappersconfigread._get_lines(content)
    assert lines == content.split('\n')


def test_get_lines_continued_line():
    content = 'vsftpd : 192.168\\\n.2.*'
    lines = tcpwrappersconfigread._get_lines(content)
    expected = ['vsftpd : 192.168.2.*']
    assert lines == expected


def test_get_lines_backslash_followed_by_whitespace():
    content = 'foo \\ \nthis is not a continuation line'
    lines = tcpwrappersconfigread._get_lines(content)
    expected = ['foo \\ ', 'this is not a continuation line']
    assert lines == expected


def test_get_lines_continued_comment():
    content = '# foo \\\n' \
              'this is still a comment'
    lines = tcpwrappersconfigread._get_lines(content)
    expected = ['# foo this is still a comment']
    assert lines == expected


def test_is_comment():
    assert tcpwrappersconfigread._is_comment('') is True
    assert tcpwrappersconfigread._is_comment('  ') is True
    assert tcpwrappersconfigread._is_comment('# foo') is True
    assert tcpwrappersconfigread._is_comment('#') is True
    assert tcpwrappersconfigread._is_comment(' # foo') is False
    assert tcpwrappersconfigread._is_comment('foo') is False
    assert tcpwrappersconfigread._is_comment(' foo') is False


def test_get_daemon_lists_in_file():
    path = '/etc/hosts.allow'
    reader = MockFileReader()
    reader.files[path] = 'vsftpd : 192.168.2.*\n' \
                         'ALL : 192.168.1.*\n'

    daemon_lists = tcpwrappersconfigread._get_daemon_lists_in_file(path, read_func=reader.read)

    num_lines = 2
    assert len(daemon_lists) == num_lines
    assert daemon_lists[0].value == ['vsftpd']
    assert daemon_lists[1].value == ['ALL']


def test_get_daemon_lists_in_file_nonexistent():
    reader = MockFileReader()
    daemon_lists = tcpwrappersconfigread._get_daemon_lists_in_file('/etc/hosts.allow', read_func=reader.read)
    assert not daemon_lists


def test_get_daemon_lists():
    reader = MockFileReader()
    reader.files['/etc/hosts.allow'] = 'vsftpd : 192.168.2.*\n' \
                                       'ALL : 192.168.1.*\n'
    reader.files['/etc/hosts.deny'] = 'sendmail : 192.168.2.*\n'

    daemon_lists = tcpwrappersconfigread._get_daemon_lists(read_func=reader.read)

    num_lines = 3
    assert len(daemon_lists) == num_lines
    assert daemon_lists[0].value == ['vsftpd']
    assert daemon_lists[1].value == ['ALL']
    assert daemon_lists[2].value == ['sendmail']


def test_get_daemon_lists_nonexistent_config():
    reader = MockFileReader()
    daemon_lists = tcpwrappersconfigread._get_daemon_lists(read_func=reader.read)
    assert not daemon_lists


def test_get_tcp_wrappers_facts():
    reader = MockFileReader()
    reader.files['/etc/hosts.allow'] = 'vsftpd : 192.168.2.*\n' \
                                       'ALL : 192.168.1.*\n'
    reader.files['/etc/hosts.deny'] = 'sendmail : 192.168.2.*\n'

    facts = tcpwrappersconfigread.get_tcp_wrappers_facts(read_func=reader.read)

    num_lines = 3
    assert len(facts.daemon_lists) == num_lines
    assert facts.daemon_lists[0].value == ['vsftpd']
    assert facts.daemon_lists[1].value == ['ALL']
    assert facts.daemon_lists[2].value == ['sendmail']


def test_get_tcp_wrappers_facts_nonexistent_config():
    reader = MockFileReader()
    facts = tcpwrappersconfigread.get_tcp_wrappers_facts(read_func=reader.read)
    assert not facts.daemon_lists
