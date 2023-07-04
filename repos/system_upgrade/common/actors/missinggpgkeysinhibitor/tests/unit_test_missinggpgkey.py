import os
import shutil
import sys
import tempfile

import distro
import pytest

from leapp.libraries.actor.missinggpgkey import _expand_vars, _get_abs_file_path, _get_repo_gpgkey_urls
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import InstalledRPM, RepositoryData, RPM, TargetUserSpaceInfo


@pytest.mark.parametrize('data, exp', [
    ('bare string', 'bare string'),
    ('with dollar$$$', 'with dollar$$$'),
    ('path/with/$basearch/something', 'path/with/x86_64/something'),
    ('path/with/$releasever/something', 'path/with/9/something'),
    ('path/with/$releasever/$basearch', 'path/with/9/x86_64'),
    ('path/with/$releasever/$basearch', 'path/with/9/x86_64'),
])
def test_expand_vars(monkeypatch, data, exp):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver='9.1'))  # x86_64 arch is default
    res = _expand_vars(data)
    assert res == exp


@pytest.mark.parametrize('repo, exp', [
    (RepositoryData(repoid='dummy', name='name'), None),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{}'), None),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgcheck":"1"}'), None),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgcheck":"0"}'), []),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgcheck":"no"}'), []),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgcheck":"False"}'), []),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgkey":"dummy"}'), ["dummy"]),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgcheck":"1","gpgkey":"dummy"}'),
     ["dummy"]),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgkey":"dummy, another"}'),
     ["dummy", "another"]),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgkey":"dummy\\nanother"}'),
     ["dummy", "another"]),
    (RepositoryData(repoid='dummy', name='name', additional_fields='{"gpgkey":"$releasever"}'),
     ["9"]),
])
def test_get_repo_gpgkey_urls(monkeypatch, repo, exp):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver='9.1'))
    keys = _get_repo_gpgkey_urls(repo)
    assert keys == exp


@pytest.mark.parametrize('target_userspace, file_url, exists_in_container, exp', [
    (TargetUserSpaceInfo(path='/', scratch='', mounts=''), 'file:///path/to/key', True, '/path/to/key'),
    (TargetUserSpaceInfo(path='/', scratch='', mounts=''), 'file:///path/to/key', False, '/path/to/key'),
    (TargetUserSpaceInfo(path='/path/to/container/', scratch='', mounts=''), 'file:///path/to/key', True,
     '/path/to/container/path/to/key'),
    (TargetUserSpaceInfo(path='/path/to/container/', scratch='', mounts=''), 'file:///path/to/key', False,
     '/path/to/key'),
    (TargetUserSpaceInfo(path='/path/to/container/', scratch='', mounts=''), 'https://example.com/path/to/key',
     True, 'https://example.com/path/to/key'),
    (TargetUserSpaceInfo(path='/path/to/container/', scratch='', mounts=''), 'https://example.com/path/to/key',
     False, 'https://example.com/path/to/key'),
])
def test_get_abs_file_path(monkeypatch, target_userspace, file_url, exists_in_container, exp):
    def os_path_exists_mocked(path):
        if path == os.path.join(target_userspace.path, file_url[8:]) and exists_in_container:
            return True
        return False

    monkeypatch.setattr('os.path.exists', os_path_exists_mocked)
    path = _get_abs_file_path(target_userspace, file_url)
    assert path == exp
