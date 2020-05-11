import errno
import os

from leapp.libraries.actor import vsftpdconfigread
from leapp.libraries.common.testutils import make_IOError, make_OSError
from leapp.models import InstalledRedHatSignedRPM, RPM


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


def test_parse_config():
    content = 'anonymous_enable=YES'
    path = 'my_file'

    parsed = vsftpdconfigread._parse_config(path, content)

    assert parsed['anonymous_enable'] is True


def test_parsing_bad_config_gives_None():
    content = 'foo'
    path = 'my_file'

    parsed = vsftpdconfigread._parse_config(path, content)

    assert parsed is None


def test_get_parsed_configs():
    directory = '/etc/vsftpd'
    file_names = ['vsftpd.conf', 'foo.conf']
    listdir = MockListDir(directory, file_names)
    fileops = MockFileOperations()
    fileops.files[os.path.join(directory, file_names[0])] = 'anonymous_enable=YES\n' \
                                                            'ca_certs_file=/foo/bar\n'
    fileops.files[os.path.join(directory, file_names[1])] = 'anonymous_enable=NO\n'

    parsed_configs = list(vsftpdconfigread._get_parsed_configs(read_func=fileops.read,
                                                               listdir=listdir.listdir))

    assert not listdir.error
    assert len(fileops.files_read) == 2
    assert os.path.join(directory, file_names[0]) in fileops.files_read
    assert os.path.join(directory, file_names[1]) in fileops.files_read
    assert len(parsed_configs) == 2
    if parsed_configs[0][0] != os.path.join(directory, file_names[0]):
        parsed_configs.reverse()
    assert (os.path.join(directory, file_names[0]), {'anonymous_enable': True,
                                                     'ca_certs_file': '/foo/bar'}) in parsed_configs
    assert (os.path.join(directory, file_names[1]), {'anonymous_enable': False}) in parsed_configs


def test_get_parsed_configs_empty_dir():
    directory = '/etc/vsftpd'
    listdir = MockListDir(directory, [])
    fileops = MockFileOperations()

    parsed_configs = vsftpdconfigread._get_parsed_configs(read_func=fileops.read,
                                                          listdir=listdir.listdir)

    assert not listdir.error
    assert fileops.read_called == 0
    assert not parsed_configs


def test_get_parsed_configs_nonexistent_dir():
    listdir = MockListDir(to_raise=make_OSError(errno.ENOENT))
    fileops = MockFileOperations()

    parsed_configs = vsftpdconfigread._get_parsed_configs(read_func=fileops.read,
                                                          listdir=listdir.listdir)

    assert fileops.read_called == 0
    assert not parsed_configs


def test_get_parsed_configs_inaccessible_dir():
    listdir = MockListDir(to_raise=make_OSError(errno.EACCES))
    fileops = MockFileOperations()

    parsed_configs = vsftpdconfigread._get_parsed_configs(read_func=fileops.read,
                                                          listdir=listdir.listdir)

    assert fileops.read_called == 0
    assert not parsed_configs


def test_get_vsftpd_facts():
    directory = '/etc/vsftpd'
    file_names = ['vsftpd.conf', 'foo.conf', 'bar.conf']
    listdir = MockListDir(directory, file_names)
    fileops = MockFileOperations()
    fileops.files[os.path.join(directory, file_names[0])] = 'anonymous_enable=YES\n' \
                                                            'ca_certs_file=/foo/bar\n'
    fileops.files[os.path.join(directory, file_names[1])] = 'anonymous_enable=NO\n' \
                                                            'tcp_wrappers=YES\n'
    fileops.files[os.path.join(directory, file_names[2])] = 'strict_ssl_read_eof=yes\n' \
                                                            'tcp_wrappers=no\n'

    facts = vsftpdconfigread.get_vsftpd_facts(read_func=fileops.read, listdir=listdir.listdir)

    assert facts.default_config_hash == '892bae7b69eb66ec16afe842a15e53a5242155a4'
    assert len(facts.configs) == 3
    used_indices = set()
    for config in facts.configs:
        assert os.path.dirname(config.path) == directory
        file_name = os.path.basename(config.path)
        ix = file_names.index(file_name)
        if ix in used_indices:
            assert False
        used_indices.add(ix)
        if ix == 0:
            assert config.strict_ssl_read_eof is None
            assert config.tcp_wrappers is None
        elif ix == 1:
            assert config.strict_ssl_read_eof is None
            assert config.tcp_wrappers is True
        elif ix == 2:
            assert config.strict_ssl_read_eof is True
            assert config.tcp_wrappers is False
        else:
            assert False


def test_get_vsftpd_facts_empty_dir():
    listdir = MockListDir('/etc/vsftpd', [])
    fileops = MockFileOperations()

    facts = vsftpdconfigread.get_vsftpd_facts(read_func=fileops.read, listdir=listdir.listdir)

    assert facts.default_config_hash is None
    assert not facts.configs


def test_get_vsftpd_facts_nonexistent_dir():
    listdir = MockListDir(to_raise=make_OSError(errno.ENOENT))
    fileops = MockFileOperations()

    facts = vsftpdconfigread.get_vsftpd_facts(read_func=fileops.read, listdir=listdir.listdir)

    assert facts.default_config_hash is None
    assert not facts.configs


def test_get_vsftpd_facts_inaccessible_dir():
    listdir = MockListDir(to_raise=make_OSError(errno.EACCES))
    fileops = MockFileOperations()

    facts = vsftpdconfigread.get_vsftpd_facts(read_func=fileops.read, listdir=listdir.listdir)

    assert facts.default_config_hash is None
    assert not facts.configs


def test_is_processable_vsftpd_installed():
    installed_rpms = [
        RPM(name='sendmail', version='8.14.7', release='5.el7', epoch='0',
            packager='foo', arch='x86_64', pgpsig='bar'),
        RPM(name='vsftpd', version='3.0.2', release='25.el7', epoch='0',
            packager='foo', arch='x86_64', pgpsig='bar'),
        RPM(name='postfix', version='2.10.1', release='7.el7', epoch='0',
            packager='foo', arch='x86_64', pgpsig='bar')]
    installed_rpm_facts = InstalledRedHatSignedRPM(items=installed_rpms)

    res = vsftpdconfigread.is_processable(installed_rpm_facts)

    assert res is True


def test_is_processable_vsftpd_not_installed():
    installed_rpms = [
        RPM(name='sendmail', version='8.14.7', release='5.el7', epoch='0',
            packager='foo', arch='x86_64', pgpsig='bar'),
        RPM(name='postfix', version='2.10.1', release='7.el7', epoch='0',
            packager='foo', arch='x86_64', pgpsig='bar')]
    installed_rpm_facts = InstalledRedHatSignedRPM(items=installed_rpms)

    res = vsftpdconfigread.is_processable(installed_rpm_facts)

    assert res is False
