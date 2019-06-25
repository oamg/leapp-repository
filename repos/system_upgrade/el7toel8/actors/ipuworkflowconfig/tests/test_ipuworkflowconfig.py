import os

import pytest

from leapp.libraries.actor import library


def _clean_leapp_envs(monkeypatch):
    """
    Clean all LEAPP environment variables before running the test to have
    fresh env.
    """
    for k, _ in os.environ.items():
        if k.startswith('LEAPP'):
            monkeypatch.delenv(k)


def test_leapp_env_vars(monkeypatch):
    _clean_leapp_envs(monkeypatch)
    monkeypatch.setenv('LEAPP_VERBOSE', '1')
    monkeypatch.setenv('LEAPP_DEBUG', '1')
    monkeypatch.setenv('LEAPP_WHATEVER', '0')
    monkeypatch.setenv('LEAPP_CURRENT_PHASE', 'test')
    monkeypatch.setenv('LEAPP_CURRENT_ACTOR', 'test')
    monkeypatch.setenv('TEST', 'test')
    monkeypatch.setenv('TEST2', 'test')

    assert len(library.get_env_vars()) == 3
