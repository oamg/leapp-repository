import os

import pytest

from leapp.libraries.actor import library
from leapp.libraries.common import reporting
from leapp.libraries.common.testutils import produce_mocked, report_generic_mocked
from leapp.models import OSRelease


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
    monkeypatch.setenv('LEAPP_WHATEVER', '0')
    monkeypatch.setenv('LEAPP_VERBOSE', '1')
    monkeypatch.setenv('LEAPP_DEBUG', '1')
    monkeypatch.setenv('LEAPP_CURRENT_PHASE', 'test')
    monkeypatch.setenv('LEAPP_CURRENT_ACTOR', 'test')
    monkeypatch.setenv('TEST', 'test')
    monkeypatch.setenv('TEST2', 'test')

    assert len(library.get_env_vars()) == 1


def test_get_os_release_info(monkeypatch):
    monkeypatch.setattr('leapp.libraries.stdlib.api.produce', produce_mocked())
    monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())

    expected = OSRelease(
        release_id='rhel',
        name='Red Hat Enterprise Linux Server',
        pretty_name='Red Hat Enterprise Linux',
        version='7.6 (Maipo)',
        version_id='7.6',
        variant='Server',
        variant_id='server')
    assert expected == library.get_os_release('tests/files/os-release')

    assert not library.get_os_release('tests/files/non-existent-file')
    assert reporting.report_generic.called == 1
    assert 'inhibitor' in reporting.report_generic.report_fields['flags']
