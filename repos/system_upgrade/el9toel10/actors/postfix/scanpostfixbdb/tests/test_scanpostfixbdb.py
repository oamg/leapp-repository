import os
import shutil

import pytest

from leapp.libraries.actor import scanpostfixbdb
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
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


def _copy_cf(leapp_tmpdir, src_name, dest_name='main.cf'):
    dest = os.path.join(leapp_tmpdir, dest_name)
    shutil.copy(os.path.join(FILES_DIR, src_name), dest)
    return dest


def test_iter_config_files_directory(leapp_tmpdir):
    confdir = os.path.join(leapp_tmpdir, 'postfix')
    os.makedirs(confdir)
    for name in ('main.cf', 'master.cf'):
        with open(os.path.join(confdir, name), 'w') as handle:
            handle.write('# placeholder\n')
    with open(os.path.join(confdir, 'README'), 'w') as handle:
        handle.write('not a postfix config\n')

    found = list(scanpostfixbdb._iter_config_files([confdir]))
    assert [os.path.basename(path) for path in found] == ['main.cf', 'master.cf']


def test_iter_config_files_explicit_cf(leapp_tmpdir):
    path = _copy_cf(leapp_tmpdir, 'main.cf.hash')
    assert list(scanpostfixbdb._iter_config_files([path])) == [path]


def test_iter_config_files_skips_non_cf_file(leapp_tmpdir):
    path = os.path.join(leapp_tmpdir, 'main.cf.hash')
    with open(path, 'w') as handle:
        handle.write('alias_maps = hash:/etc/aliases\n')
    assert list(scanpostfixbdb._iter_config_files([path])) == []


def test_iter_config_files_unreadable_dir(monkeypatch, leapp_tmpdir):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    def _fail(_path):
        raise OSError('permission denied')

    monkeypatch.setattr(os, 'listdir', _fail)
    assert list(scanpostfixbdb._iter_config_files([leapp_tmpdir])) == []
    assert api.current_logger.warnmsg


def test_scan_file_hash_maps(leapp_tmpdir):
    path = _copy_cf(leapp_tmpdir, 'main.cf.hash')
    occurrences = scanpostfixbdb._scan_file(path)
    joined = '\n'.join(occurrences)
    assert len(occurrences) == 3
    assert 'alias_maps = hash:/etc/aliases' in joined
    assert 'alias_database = hash:/etc/aliases' in joined
    assert 'default_database_type = hash' in joined
    assert 'commented' not in joined


def test_scan_file_master_cf_overrides(leapp_tmpdir):
    path = _copy_cf(leapp_tmpdir, 'master.cf.hash', 'master.cf')
    occurrences = scanpostfixbdb._scan_file(path)
    joined = '\n'.join(occurrences)
    assert len(occurrences) == 2
    assert '-o virtual_alias_maps=hash:/etc/postfix/virtual' in joined
    assert '-o default_database_type=hash' in joined
    assert 'alias_maps=hash:/etc/aliases' not in joined


def test_scan_file_ignores_uppercase_hash(leapp_tmpdir):
    path = os.path.join(leapp_tmpdir, 'main.cf')
    with open(path, 'w') as handle:
        handle.write('alias_maps = HASH:/etc/aliases\n')
        handle.write('default_database_type = HASH\n')
    assert scanpostfixbdb._scan_file(path) == []


def test_scan_file_undecodable(monkeypatch, leapp_tmpdir):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    path = os.path.join(leapp_tmpdir, 'main.cf')
    with open(path, 'wb') as handle:
        handle.write(b'\xff\xfe hash:/etc/aliases\n')
    assert scanpostfixbdb._scan_file(path) == []
    assert api.current_logger.warnmsg


def test_scan_postfix_not_installed(monkeypatch, leapp_tmpdir):
    _mock_packages(monkeypatch, ['sed'])
    conf = _copy_cf(leapp_tmpdir, 'main.cf.hash')
    result = scanpostfixbdb.scan_postfix_configuration(conf_paths=[conf])
    assert result.postfix_present is False
    assert result.bdb_occurrences == []


def test_scan_hash_maps(monkeypatch, leapp_tmpdir):
    _mock_packages(monkeypatch, ['postfix'])
    conf = _copy_cf(leapp_tmpdir, 'main.cf.hash')
    result = scanpostfixbdb.scan_postfix_configuration(conf_paths=[conf])
    assert result.postfix_present is True
    assert len(result.bdb_occurrences) == 3
    joined = '\n'.join(result.bdb_occurrences)
    assert 'alias_maps = hash:/etc/aliases' in joined
    assert 'alias_database = hash:/etc/aliases' in joined
    assert 'default_database_type = hash' in joined
    assert 'commented' not in joined


def test_scan_lmdb_maps_ignored(monkeypatch, leapp_tmpdir):
    _mock_packages(monkeypatch, ['postfix'])
    conf = _copy_cf(leapp_tmpdir, 'main.cf.lmdb')
    result = scanpostfixbdb.scan_postfix_configuration(conf_paths=[conf])
    assert result.postfix_present is True
    assert result.bdb_occurrences == []


def test_scan_proxy_hash_and_btree(monkeypatch, leapp_tmpdir):
    _mock_packages(monkeypatch, ['postfix'])
    conf = _copy_cf(leapp_tmpdir, 'main.cf.proxyhash')
    result = scanpostfixbdb.scan_postfix_configuration(conf_paths=[conf])
    assert result.postfix_present is True
    assert len(result.bdb_occurrences) == 2
    joined = '\n'.join(result.bdb_occurrences)
    assert 'proxy:hash:/etc/postfix/sasl_passwd' in joined
    assert 'btree:/etc/postfix/virtual' in joined


def test_scan_master_cf_and_main_cf_directory(monkeypatch, leapp_tmpdir):
    _mock_packages(monkeypatch, ['postfix'])
    confdir = os.path.join(leapp_tmpdir, 'postfix')
    os.makedirs(confdir)
    shutil.copy(os.path.join(FILES_DIR, 'main.cf.lmdb'), os.path.join(confdir, 'main.cf'))
    shutil.copy(os.path.join(FILES_DIR, 'master.cf.hash'), os.path.join(confdir, 'master.cf'))
    with open(os.path.join(confdir, 'notes.txt'), 'w') as handle:
        handle.write('alias_maps = hash:/etc/aliases\n')

    result = scanpostfixbdb.scan_postfix_configuration(conf_paths=[confdir])
    assert result.postfix_present is True
    joined = '\n'.join(result.bdb_occurrences)
    assert 'master.cf' in joined
    assert '-o virtual_alias_maps=hash:/etc/postfix/virtual' in joined
    assert '-o default_database_type=hash' in joined
    assert 'notes.txt' not in joined
    assert 'alias_maps = hash:/etc/aliases' not in joined


@pytest.mark.parametrize('missing', [
    'does-not-exist.cf',
    'missing-dir',
])
def test_scan_missing_path(monkeypatch, leapp_tmpdir, missing):
    _mock_packages(monkeypatch, ['postfix'])
    result = scanpostfixbdb.scan_postfix_configuration(
        conf_paths=[os.path.join(leapp_tmpdir, missing)]
    )
    assert result.postfix_present is True
    assert result.bdb_occurrences == []
