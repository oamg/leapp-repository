import os

import pytest

from leapp.libraries.actor import scancryptopolicies
from leapp.libraries.common.config import version
from leapp.models import CryptoPolicyInfo


@pytest.mark.parametrize(('source_version', 'should_run'), [
    ('8', True),
    ('9', True),
])
def test_actor_execution(monkeypatch, current_actor_context, source_version, should_run):
    def read_current_policy_mock(filename):
        return "DEFAULT_XXX"

    def listdir_mock(path):
        if path == '/etc/crypto-policies/policies':
            return ['modules']
        if path == '/etc/crypto-policies/policies/modules':
            return []
        if path == '/usr/share/crypto-policies/policies':
            return ['modules', 'DEFAULT', 'FUTURE', 'FIPS', 'LEGACY']
        if path == '/usr/share/crypto-policies/policies/modules':
            return ['SHA1', 'TEST-PQ', 'OSPP']
        return _original_listdir(path)

    def isfile_mock(filename):
        if filename.endswith('/modules'):
            return False
        return True

    monkeypatch.setattr(version, 'get_source_major_version', lambda: source_version)
    monkeypatch.setattr(scancryptopolicies, 'read_current_policy', read_current_policy_mock)
    _original_listdir = os.listdir
    monkeypatch.setattr(os, 'listdir', listdir_mock)
    monkeypatch.setattr(os.path, 'isfile', isfile_mock)
    current_actor_context.run()
    if should_run:
        cpi = current_actor_context.consume(CryptoPolicyInfo)
        assert cpi
        assert cpi[0].current_policy == 'DEFAULT_XXX'
    else:
        assert not current_actor_context.consume(CryptoPolicyInfo)
