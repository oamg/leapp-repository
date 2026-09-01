import os

import pytest

from leapp.libraries.actor import scanpostfixbdb
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, RPM

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = os.path.join(CUR_DIR, 'files')


def _rpm(name):
    return RPM(name=name,
               version='0.1',
               release='1.sm01',
               epoch='1',
               pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51',
               packager='Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>',
               arch='noarch')


def _mock_packages(monkeypatch, names):
    rpms = [_rpm(name) for name in names]
    monkeypatch.setattr(
        api,
        'current_actor',
        CurrentActorMocked(msgs=[DistributionSignedRPM(items=rpms)]),
    )


def test_scan_postfix_not_installed(monkeypatch):
    _mock_packages(monkeypatch, ['sed'])
    result = scanpostfixbdb.scan_postfix_configuration(
        conf_paths=[os.path.join(FILES_DIR, 'main.cf.hash')]
    )
    assert result.postfix_present is False
    assert result.bdb_occurrences == []


def test_scan_hash_maps(monkeypatch):
    _mock_packages(monkeypatch, ['postfix'])
    conf = os.path.join(FILES_DIR, 'main.cf.hash')
    result = scanpostfixbdb.scan_postfix_configuration(conf_paths=[conf])
    assert result.postfix_present is True
    assert len(result.bdb_occurrences) == 3
    joined = '\n'.join(result.bdb_occurrences)
    assert 'alias_maps = hash:/etc/aliases' in joined
    assert 'alias_database = hash:/etc/aliases' in joined
    assert 'default_database_type = hash' in joined
    assert 'commented' not in joined


def test_scan_lmdb_maps_ignored(monkeypatch):
    _mock_packages(monkeypatch, ['postfix'])
    conf = os.path.join(FILES_DIR, 'main.cf.lmdb')
    result = scanpostfixbdb.scan_postfix_configuration(conf_paths=[conf])
    assert result.postfix_present is True
    assert result.bdb_occurrences == []


def test_scan_proxy_hash_and_btree(monkeypatch):
    _mock_packages(monkeypatch, ['postfix'])
    conf = os.path.join(FILES_DIR, 'main.cf.proxyhash')
    result = scanpostfixbdb.scan_postfix_configuration(conf_paths=[conf])
    assert result.postfix_present is True
    assert len(result.bdb_occurrences) == 2
    joined = '\n'.join(result.bdb_occurrences)
    assert 'proxy:hash:/etc/postfix/sasl_passwd' in joined
    assert 'btree:/etc/postfix/virtual' in joined


@pytest.mark.parametrize('missing', [
    os.path.join(FILES_DIR, 'does-not-exist.cf'),
    os.path.join(FILES_DIR, 'missing-dir'),
])
def test_scan_missing_path(monkeypatch, missing):
    _mock_packages(monkeypatch, ['postfix'])
    result = scanpostfixbdb.scan_postfix_configuration(conf_paths=[missing])
    assert result.postfix_present is True
    assert result.bdb_occurrences == []
