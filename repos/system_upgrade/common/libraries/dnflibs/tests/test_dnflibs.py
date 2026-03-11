import pytest

from leapp.libraries.common import dnflibs
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api


class MockSubstitutions(dict):
    def update_from_etc(self, path):
        pass


class MockDNFConf:
    def __init__(self):
        self.substitutions = MockSubstitutions({'releasever': '8'})

    def read(self):
        pass


class MockDNFBase:
    def __init__(self, conf=None):
        self.conf = conf or MockDNFConf()
        self._fill_sack_called = False

    def read(self):
        pass

    def init_plugins(self):
        pass

    def read_all_repos(self):
        pass

    def configure_plugins(self):
        pass

    def fill_sack(self):
        self._fill_sack_called = True


class MockDNF:
    """Mock dnf module"""
    class conf:
        Conf = MockDNFConf

    Base = MockDNFBase

    class exceptions:
        RepoError = Exception


def test_create_dnf_base_success(monkeypatch):
    """
    Test successful creation and initialization of dnf.Base
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='8.10'))
    monkeypatch.setattr(dnflibs, 'dnf', MockDNF)

    base = dnflibs.create_dnf_base()

    assert base is not None
    assert isinstance(base, MockDNFBase)
    assert base._fill_sack_called


@pytest.mark.parametrize('error_message,expected_repoid', [
    ('Failed to download metadata for repo: test-repo', 'test-repo'),
    ('Error with repo: "my-repo"', 'my-repo'),
    ("Failed for repo: 'quoted-repo'", 'quoted-repo'),
    ('Generic error without repo information', 'unknown repo'),
])
def test_create_dnf_base_repo_error(monkeypatch, error_message, expected_repoid):
    class RepoError(Exception):
        pass

    class MockExceptions:
        pass

    MockExceptions.RepoError = RepoError

    class FailingMockDNFBase:
        _repo_error = RepoError
        _error_message = error_message

        def __init__(self, conf=None):
            self.conf = conf or MockDNFConf()

        def read(self):
            pass

        def init_plugins(self):
            pass

        def read_all_repos(self):
            pass

        def configure_plugins(self):
            pass

        def fill_sack(self):
            raise self._repo_error(self._error_message)

    class FailingMockDNF:
        class conf:
            Conf = MockDNFConf

        Base = FailingMockDNFBase
        exceptions = MockExceptions

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='8.10'))
    monkeypatch.setattr(dnflibs, 'dnf', FailingMockDNF)

    with pytest.raises(dnflibs.DNFRepoError) as exc_info:
        dnflibs.create_dnf_base()

    assert 'DNF failed to load repositories' in str(exc_info.value)
    assert expected_repoid in str(exc_info.value.details['hint'])
