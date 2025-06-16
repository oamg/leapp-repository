import os
import random

import pytest

from leapp.libraries.actor import sssdupdate
from leapp.models import KnownHostsProxyConfig


class MockedFile:
    """
    Mocks a file to avoid writing to the filesystem.

    This is the minimum mocking required for this test.
    Most of the file functions are not implemented.
    Only those required by this test.
    """
    def __init__(self, name: str, fs):
        self.name = name
        self.fs = fs
        self.fd = -1
        self.mode = 0o644
        self.contents = ''

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def open(self, fd: int, mode: str):
        self.fd = fd
        if mode in ['w', 'x']:
            self.contents = ''

    def fileno(self):
        return self.fd

    def write(self, text: str) -> int:
        self.contents += text
        return len(text)

    def __iter__(self):
        return iter(self.contents.splitlines(keepends=True))

    def close(self):
        self.fs._close(self.fd)
        self.fd = -1


class MockedStatResults:
    def __init__(self, mode):
        self.st_mode = mode


class MockedFileSystem:
    """
    Mocks a filesystem.

    Simulates the minimum services needed by the tests in this file.
    """
    def __init__(self):
        self._by_name = {}
        self._by_fd = []

    def _get_by_fd(self, fd: int) -> MockedFile:
        try:
            return self._by_fd[fd]
        except IndexError:
            raise OSError('Bad file descriptor')

    def _get_by_name(self, name: str) -> MockedFile:
        try:
            return self._by_name[name]
        except KeyError:
            raise FileNotFoundError(name)

    def fstat(self, fd: int) -> MockedStatResults:
        return MockedStatResults(self._get_by_fd(fd).mode)

    def fchmod(self, fd: int, mode: int):
        file = self._get_by_fd(fd)
        file.mode = mode

    def replace(self, src: str, dest: str):
        file = self._get_by_name(src)
        self._by_name[dest] = file

    def unlink(self, name: str):
        del self._by_name[name]

    def open(self, name: str, mode: str) -> MockedFile:
        if name not in self._by_name:
            file = MockedFile(name, self)
            self._by_name[name] = file
        else:
            if mode == 'x':
                raise FileExistsError('File exists: ' + name)
            file = self._by_name[name]

        self._by_fd.append(file)
        fd = len(self._by_fd) - 1
        file.open(fd, mode)

        return file

    def _close(self, fd: int):
        # This function is called by MockedFile.close()
        self._by_fd[fd] = None


mocked_filesystem = MockedFileSystem()


@pytest.fixture(autouse=True)
def mock_filesystem(monkeypatch):
    def mocked_open(name, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        return mocked_filesystem.open(name, mode)

    def mocked_fchmod(fd: int, mode: int):
        mocked_filesystem.fchmod(fd, mode)

    def mocked_fstat(fd: int) -> MockedStatResults:
        return mocked_filesystem.fstat(fd)

    def mocked_replace(src: str, dest: str):
        mocked_filesystem.replace(src, dest)

    def mocked_unlink(name: str):
        mocked_filesystem.unlink(name)

    monkeypatch.setattr("builtins.open", mocked_open)
    monkeypatch.setattr(os, "fchmod", mocked_fchmod)
    monkeypatch.setattr(os, "fstat", mocked_fstat)
    monkeypatch.setattr(os, "replace", mocked_replace)
    monkeypatch.setattr(os, "unlink", mocked_unlink)


def make_mock_file(contents: str) -> str:
    name = os.path.join('/tmp', f'file.{str(random.uniform(1, 999999))}')
    with mocked_filesystem.open(name, 'w') as file:
        file.write(contents)

    return name


def make_files(contents: list[str]) -> list[str]:
    files = []
    for conts in contents:
        files.append(make_mock_file(conts))

    return files


def check_file(name: str, expected: str):
    assert name in mocked_filesystem._by_name.keys()  # False positive => pylint: disable=consider-iterating-dictionary
    assert mocked_filesystem._by_name[name].contents == expected


@pytest.mark.parametrize('sssd', [True, False])
def test_sssdupdate__no_change(monkeypatch, sssd: bool):
    contents = [
        """
        XXXXX XXXXXXXXX XXXXXXXXXXXX XXXXXXXXX
        YYYYYYYY YYYYYY YYYYYYY YYYYYYYYYY
        ZZZZZZ ZZZZZZZ ZZZZZZZ ZZZZZZZ ZZZZZZZ
        AAAAAAA AAAAAAAAAA AAAAA
        BBBBBBBB BBBBBBBBBB BBBBBBB BBBBB
        CCCCCCCC CCCCCCC CCCCCCCC CCCCCCC
        """,
        """
        xxxxxx xxxxxxxxx xxxxxxxxx
        yyyyyyyyy yyyyyyyyy yyyyyyyyyyyyyy
        zzzzz zzzzzzz zzzzzzzzzzzz zzz
        aaaaaa aaaaaaaa aaaaaaaaa aaaaaaaa
        bbbbbbbb bbbbbbbbbb bbbbbbbb
        """
    ]

    files = make_files(contents)
    if sssd:
        config = KnownHostsProxyConfig(sssd_config_files=files)
    else:
        config = KnownHostsProxyConfig(ssh_config_files=files)

    sssdupdate.update_config(config)

    for i in range(len(contents)):
        check_file(files[i], contents[i])


def test_sssdupdate__sssd_change(monkeypatch):
    contents = [
        """
        [sssd]
        services = pam, nss
        domains = test
        """,
        """
        [sssd]
        # services = pam,nss
        domains = test
        """,
        """
        [sssd]
        services = pam,ssh,nss
        domains = test
        """
    ]
    expected = [
        """
        [sssd]
        services = pam, nss,ssh
        domains = test
        """,
        """
        [sssd]
        # services = pam,nss,ssh
        domains = test
        """,
        """
        [sssd]
        services = pam,ssh,nss
        domains = test
        """
    ]
    # A failure here indicates an error in the test
    assert len(contents) == len(expected)

    sssd_files = make_files(contents)
    ssh_files = make_files([''])
    config = KnownHostsProxyConfig(sssd_config_files=sssd_files, ssh_config_files=ssh_files)

    sssdupdate.update_config(config)

    for i in range(len(expected)):
        check_file(sssd_files[i], expected[i])


def test_sssdupdate__ssh_change(monkeypatch):
    contents = [
        """
        First line
        ProxyCommand  /usr/bin/sss_ssh_knownhostsproxy -p %p -d domain %h
        3rd line
        """,
        """
        #\tProxyCommand /usr/bin/sss_ssh_knownhostsproxy --port=%p  %h
        # Another comment
        """
    ]
    expected = [
        """
        First line
        KnownHostsCommand  /usr/bin/sss_ssh_knownhosts   -d domain %H
        3rd line
        """,
        """
        #\tKnownHostsCommand /usr/bin/sss_ssh_knownhosts   %H
        # Another comment
        """
    ]
    # A failure here indicates an error in the test
    assert len(contents) == len(expected)

    files = make_files(contents)
    config = KnownHostsProxyConfig(ssh_config_files=files)

    sssdupdate.update_config(config)

    for i in range(len(expected)):
        check_file(files[i], expected[i])
