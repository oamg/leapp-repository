import os

from leapp.libraries.actor import scancryptopolicies
from leapp.models import CryptoPolicyInfo


def test_actor_execution(monkeypatch, current_actor_context):
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
        return not filename.endswith('/modules')

    monkeypatch.setattr(scancryptopolicies, 'read_current_policy', read_current_policy_mock)
    _original_listdir = os.listdir
    monkeypatch.setattr(os, 'listdir', listdir_mock)
    monkeypatch.setattr(os.path, 'isfile', isfile_mock)
    current_actor_context.run()

    cpi = current_actor_context.consume(CryptoPolicyInfo)
    assert cpi
    assert cpi[0].current_policy == 'DEFAULT_XXX'
