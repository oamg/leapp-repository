import os

from leapp.libraries.actor import sssd_cache_files


def glob_sssd_files(path_spec):
    if path_spec.endswith('*.ldb'):
        path_spec = path_spec[:-5]
        return list([os.path.join(path_spec, 'removed_file1.ldb'), os.path.join(path_spec, 'removed_file2.ldb')])
    return []


def test_remove_sssd_cache_files(monkeypatch):
    monkeypatch.setattr(
        sssd_cache_files.glob,
        'glob',
        glob_sssd_files)
    removed = []
    monkeypatch.setattr(sssd_cache_files.os, 'remove', removed.append)
    sssd_cache_files.remove_sssd_cache_files(None)
    assert not removed
    sssd_cache_files.remove_sssd_cache_files(True)
    assert removed == ['/var/lib/sss/db/removed_file1.ldb', '/var/lib/sss/db/removed_file2.ldb']
