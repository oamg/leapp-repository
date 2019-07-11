from collections import namedtuple

from leapp.libraries.common.config import get_env, get_all_envs
from leapp.libraries.stdlib import api
from leapp.models import EnvVar


class CurrentActorMocked(object):
    env_vars = [EnvVar(name='LEAPP_DEVEL_SKIP_WIP', value='0'),
                EnvVar(name='LEAPP_DEVEL_SKIP_DIP', value='1'),
                EnvVar(name='LEAPP_DEVEL_SKIP_RIP', value='2')]
    configuration = namedtuple('configuration', ['leapp_env_vars'])(env_vars)


def test_env_var_match(monkeypatch):

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked)
    assert get_env('LEAPP_DEVEL_SKIP_WIP') == '0'
    assert not get_env('LEAPP_DEVEL_SKIP_PIP')


def test_get_all_vars(monkeypatch):

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked)
    assert len(get_all_envs()) == 3
