import pytest

from leapp.libraries.actor import scanclienablerepo
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import CustomTargetRepository


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


def test_no_enabledrepos(monkeypatch):
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', LoggerMocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    scanclienablerepo.process()
    assert not api.current_logger.infomsg
    assert not api.produce.called


@pytest.mark.parametrize('envars,result', [
    ({'LEAPP_ENABLE_REPOS': 'repo1'}, [CustomTargetRepository(repoid='repo1')]),
    ({'LEAPP_ENABLE_REPOS': 'repo1,repo2'}, [CustomTargetRepository(repoid='repo1'),
                                             CustomTargetRepository(repoid='repo2')]),
])
def test_enabledrepos(monkeypatch, envars, result):
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', LoggerMocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(envars=envars))
    scanclienablerepo.process()
    assert api.current_logger.infomsg
    assert api.produce.called == len(result)
    for i in result:
        assert i in api.produce.model_instances
