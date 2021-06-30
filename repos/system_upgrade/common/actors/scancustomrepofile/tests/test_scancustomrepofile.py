import os

from leapp.libraries.actor import scancustomrepofile
from leapp.libraries.common import repofileutils
from leapp.libraries.common.testutils import produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import CustomTargetRepository, CustomTargetRepositoryFile, RepositoryData, RepositoryFile


_REPODATA = [
    RepositoryData(repoid="repo1", name="repo1name", baseurl="repo1url", enabled=True),
    RepositoryData(repoid="repo2", name="repo2name", baseurl="repo2url", enabled=False),
    RepositoryData(repoid="repo3", name="repo3name", enabled=True),
    RepositoryData(repoid="repo4", name="repo4name", mirrorlist="mirror4list", enabled=True),
]

_CUSTOM_REPOS = [
    CustomTargetRepository(repoid="repo1", name="repo1name", baseurl="repo1url", enabled=True),
    CustomTargetRepository(repoid="repo2", name="repo2name", baseurl="repo2url", enabled=False),
    CustomTargetRepository(repoid="repo3", name="repo3name", baseurl=None, enabled=True),
    CustomTargetRepository(repoid="repo4", name="repo4name", baseurl=None, enabled=True),
]

_CUSTOM_REPO_FILE_MSG = CustomTargetRepositoryFile(file=scancustomrepofile.CUSTOM_REPO_PATH)


class LoggerMocked(object):
    def __init__(self):
        self.infomsg = None
        self.debugmsg = None

    def info(self, msg):
        self.infomsg = msg

    def debug(self, msg):
        self.debugmsg = msg

    def __call__(self):
        return self


def test_no_repofile(monkeypatch):
    monkeypatch.setattr(os.path, 'isfile', lambda dummy: False)
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', LoggerMocked())
    scancustomrepofile.process()
    msg = "The {} file doesn't exist. Nothing to do.".format(scancustomrepofile.CUSTOM_REPO_PATH)
    assert api.current_logger.debugmsg == msg
    assert not api.produce.called


def test_valid_repofile_exists(monkeypatch):
    def _mocked_parse_repofile(fpath):
        return RepositoryFile(file=fpath, data=_REPODATA)
    monkeypatch.setattr(os.path, 'isfile', lambda dummy: True)
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(repofileutils, 'parse_repofile', _mocked_parse_repofile)
    monkeypatch.setattr(api, 'current_logger', LoggerMocked())
    scancustomrepofile.process()
    msg = "The {} file exists.".format(scancustomrepofile.CUSTOM_REPO_PATH)
    assert api.current_logger.infomsg == msg
    assert api.produce.called == len(_CUSTOM_REPOS) + 1
    assert _CUSTOM_REPO_FILE_MSG in api.produce.model_instances
    for crepo in _CUSTOM_REPOS:
        assert crepo in api.produce.model_instances


def test_empty_repofile_exists(monkeypatch):
    def _mocked_parse_repofile(fpath):
        return RepositoryFile(file=fpath, data=[])
    monkeypatch.setattr(os.path, 'isfile', lambda dummy: True)
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(repofileutils, 'parse_repofile', _mocked_parse_repofile)
    monkeypatch.setattr(api, 'current_logger', LoggerMocked())
    scancustomrepofile.process()
    msg = "The {} file exists.".format(scancustomrepofile.CUSTOM_REPO_PATH)
    assert api.current_logger.infomsg == msg
    assert not api.produce.called
