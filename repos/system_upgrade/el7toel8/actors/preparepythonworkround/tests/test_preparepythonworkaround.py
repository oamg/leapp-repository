from os import symlink, path, access, X_OK

import pytest

from leapp.libraries.actor import workaround
from leapp.libraries.common.utils import makedirs


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
