from collections import namedtuple
from os import access, path, symlink, X_OK

import pytest

from leapp.libraries.actor import workaround
from leapp.libraries.common.utils import makedirs

SysVersionInfo = namedtuple('version_info', ['major', 'minor', 'micro', 'releaselevel', 'serial'])


def fake_symlink(basedir):
    def impl(source, target):
        source_path = str(basedir.join(*source.lstrip('/').split('/')))
        makedirs(source_path)
        symlink(source_path, target)
    return impl


def test_apply_python3_workaround(monkeypatch, tmpdir):
    leapp_home = tmpdir.mkdir('tmp_leapp_py3')
    monkeypatch.setattr(workaround.os, 'symlink', fake_symlink(tmpdir.mkdir('lib')))
    monkeypatch.setattr(workaround, 'LEAPP_HOME', str(leapp_home))

    # Ensure double invocation doesn't cause a problem
    workaround.apply_python3_workaround()
    workaround.apply_python3_workaround()

    # Ensure creation of all required elements
    assert path.islink(str(leapp_home.join('leapp')))
    assert path.isfile(str(leapp_home.join('leapp3')))
    assert access(str(leapp_home.join('leapp3')), X_OK)

    assert str(leapp_home) in leapp_home.join('leapp3').read_text('utf-8')


@pytest.mark.parametrize('pydir', ('python2.7', 'python3.6', 'python3.9'))
def test_orig_leapp_path(monkeypatch, pydir):
    monkeypatch.setattr(workaround, '_get_python_dirname', lambda: pydir)
    assert workaround._get_orig_leapp_path() == '/usr/lib/{}/site-packages/leapp'.format(pydir)


@pytest.mark.parametrize('sys_version_info,result', (
    (SysVersionInfo(2, 7, 5, 'final', 0), 'python2.7'),
    (SysVersionInfo(3, 6, 0, 'X', 0), 'python3.6'),
    (SysVersionInfo(3, 9, 0, 'X', 0), 'python3.9'),
))
def test_get_python_dirname(monkeypatch, sys_version_info, result):
    monkeypatch.setattr(workaround.sys, 'version_info', sys_version_info)
    assert workaround._get_python_dirname() == result
