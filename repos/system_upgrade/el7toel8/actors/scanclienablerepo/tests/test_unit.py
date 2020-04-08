from collections import namedtuple
import os

import pytest

from leapp.libraries.actor import library
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import CustomTargetRepository
from leapp import models


class CurrentActorMocked(object):
    def __init__(self, kernel='3.10.0-957.43.1.el7.x86_64', release_id='rhel',
                 src_ver='7.6', dst_ver='8.1', arch=architecture.ARCH_X86_64,
                 envars=None):

        if envars:
            envarsList = [models.EnvVar(name=key, value=value) for key, value in envars.items()]
        else:
            envarsList = []

        version = namedtuple('Version', ['source', 'target'])(src_ver, dst_ver)
        os_release = namedtuple('OS_release', ['release_id', 'version_id'])(release_id, src_ver)
        args = (version, kernel, os_release, arch, envarsList)
        conf_fields = ['version', 'kernel', 'os_release', 'architecture', 'leapp_env_vars']
        self.configuration = namedtuple('configuration', conf_fields)(*args)
        self._common_folder = '../../files'

    def __call__(self):
        return self

    def get_common_folder_path(self, folder):
        return os.path.join(self._common_folder, folder)


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
    library.process()
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
    library.process()
    assert api.current_logger.infomsg
    assert api.produce.called == len(result)
    for i in result:
        assert i in api.produce.model_instances
