import errno

from leapp.libraries.actor.vsftpdconfigupdate import migrate_configs
from leapp.libraries.common.testutils import make_IOError
from leapp.libraries.common.vsftpdutils import VSFTPD_DEFAULT_CONFIG_PATH
from leapp.models import VsftpdConfig, VsftpdFacts


class MockFileOperations(object):
    def __init__(self):
        self.files = {}
        self.files_read = {}
        self.files_written = {}
        self.read_called = 0
        self.write_called = 0

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

    def _increment_write_counters(self, path):
        self.write_called += 1
        self.files_written.setdefault(path, 0)
        self.files_written[path] += 1

    def write(self, path, content):
        self._increment_write_counters(path)
        self.files[path] = content


def test_restoring_default_config():
    content = 'anonymous_enable=NO\n' \
              'tcp_wrappers=NO\n' \
              'strict_ssl_read_eof=NO\n'
    fileops = MockFileOperations()
    fileops.files[VSFTPD_DEFAULT_CONFIG_PATH] = content
    config = VsftpdConfig(path=VSFTPD_DEFAULT_CONFIG_PATH,
                          tcp_wrappers=False, strict_ssl_read_eof=False)
    facts = VsftpdFacts(default_config_hash='foobar', configs=[config])

    migrate_configs(facts, fileops=fileops)

    assert len(fileops.files_read) == 1
    assert VSFTPD_DEFAULT_CONFIG_PATH in fileops.files_read
    assert len(fileops.files_written) == 1
    assert VSFTPD_DEFAULT_CONFIG_PATH in fileops.files_written
    expected_lines = ['# Commented out by Leapp:',
                      '#anonymous_enable=NO',
                      'tcp_wrappers=NO',
                      'strict_ssl_read_eof=NO',
                      '',
                      '# Added by Leapp:',
                      'anonymous_enable=YES',
                      '']
    assert fileops.files[VSFTPD_DEFAULT_CONFIG_PATH] == '\n'.join(expected_lines)


def test_setting_tcp_wrappers():
    path = '/etc/vsftpd/foo.conf'
    content = 'tcp_wrappers=YES\n' \
              'strict_ssl_read_eof=NO\n'
    fileops = MockFileOperations()
    fileops.files[path] = content
    config = VsftpdConfig(path=path,
                          tcp_wrappers=True, strict_ssl_read_eof=False)
    facts = VsftpdFacts(configs=[config])

    migrate_configs(facts, fileops=fileops)

    assert path in fileops.files_read
    assert len(fileops.files_written) == 1
    assert path in fileops.files_written
    expected_lines = ['# Commented out by Leapp:',
                      '#tcp_wrappers=YES',
                      'strict_ssl_read_eof=NO',
                      '',
                      '# Added by Leapp:',
                      'tcp_wrappers=NO',
                      '']
    assert fileops.files[path] == '\n'.join(expected_lines)


def test_setting_strict_ssl_read_eof():
    path = '/etc/vsftpd/bar.conf'
    content = 'local_enable=YES\n'
    fileops = MockFileOperations()
    fileops.files[path] = content
    config = VsftpdConfig(path=path,
                          tcp_wrappers=None, strict_ssl_read_eof=None)
    facts = VsftpdFacts(configs=[config])

    migrate_configs(facts, fileops=fileops)

    assert path in fileops.files_read
    assert len(fileops.files_written) == 1
    assert path in fileops.files_written
    expected_lines = ['local_enable=YES',
                      '',
                      '# Added by Leapp:',
                      'strict_ssl_read_eof=NO',
                      '']
    assert fileops.files[path] == '\n'.join(expected_lines)
