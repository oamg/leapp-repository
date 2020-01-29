from collections import namedtuple

import pytest

from leapp.libraries.common.config import get_env, get_all_envs, get_product_type
from leapp.libraries.stdlib import api
from leapp.models import EnvVar


class CurrentActorMocked(object):
    def __init__(self, envars=None):
        if envars:
            envarsList = [EnvVar(name=key, value=value) for key, value in envars.items()]
        else:
            envarsList = []
        self.configuration = namedtuple('configuration', ['leapp_env_vars'])(envarsList)

    def __call__(self):
        return self


def test_env_var_match(monkeypatch):
    envars = {'LEAPP_DEVEL_SKIP_WIP': '0',
              'LEAPP_DEVEL_SKIP_DIP': '1',
              'LEAPP_DEVEL_SKIP_RIP': '2'}
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(envars))
    assert get_env('LEAPP_DEVEL_SKIP_WIP') == '0'
    assert not get_env('LEAPP_DEVEL_SKIP_PIP')


def test_get_all_vars(monkeypatch):
    envars = {'LEAPP_DEVEL_SKIP_WIP': '0',
              'LEAPP_DEVEL_SKIP_DIP': '1',
              'LEAPP_DEVEL_SKIP_RIP': '2'}
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(envars))
    assert api.current_actor().configuration.leapp_env_vars == get_all_envs()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    assert api.current_actor().configuration.leapp_env_vars == get_all_envs()


def test_get_product_type_valid(monkeypatch):
    prod_types = ('ga', 'beta', 'htb', 'GA', 'BETA', 'HTB', '')
    for src, dst in [(i, j) for i in prod_types for j in prod_types]:
        envars = {'LEAPP_DEVEL_SOURCE_PRODUCT_TYPE': src,
                  'LEAPP_DEVEL_TARGET_PRODUCT_TYPE': dst}
        exp_src = 'ga' if not src else src.lower()
        exp_dst = 'ga' if not dst else dst.lower()
        monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(envars))
        assert exp_src == get_product_type('source')
        assert exp_dst == get_product_type('target')
    # return 'ga' if envars are not specified
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    assert get_product_type('source') == 'ga'
    assert get_product_type('target') == 'ga'


def test_get_product_type_invalid_product(monkeypatch):
    for sys_type, envar in [('source', 'LEAPP_DEVEL_SOURCE_PRODUCT_TYPE'),
                            ('target', 'LEAPP_DEVEL_TARGET_PRODUCT_TYPE')]:
        monkeypatch.setattr(api, 'current_actor', CurrentActorMocked({envar: 'wrong'}))
        with pytest.raises(ValueError) as err:
            get_product_type(sys_type)
        assert 'Invalid value in the {} envar'.format(envar) in str(err)


def test_get_product_type_invalid_param():
    with pytest.raises(ValueError) as err:
        get_product_type('fail')
    assert 'Given invalid sys_type.' in str(err)
