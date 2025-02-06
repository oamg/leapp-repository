import os
import shutil
import tempfile

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor.scancryptopolicies import (
    _get_name_from_file,
    find_rpm_untracked,
    read_current_policy,
    read_policy_dirs
)
from leapp.models import CustomCryptoPolicy, CustomCryptoPolicyModule

NOFILE = "/tmp/non-existing-file-should-not-really-be-here"


def test_get_name_from_file():
    assert _get_name_from_file("/path/name.extension") == "name"
    assert _get_name_from_file("/othername.e") == "othername"
    assert _get_name_from_file("/other.name.e") == "other.name"
    assert _get_name_from_file("/some/long/path/other.name") == "other"
    assert _get_name_from_file("/some/long/path/no_extension") == "no_extension"


def test_find_rpm_untracked(current_actor_context):
    # this is tracked
    files = ["/tmp/"]
    assert find_rpm_untracked(files) == []
    files = ["/etc/crypto-policies/config"]
    assert find_rpm_untracked(files) == []

    # python2 compatibility :/
    dirpath = tempfile.mkdtemp()

    try:
        # the tempfile is not tracked by RPM
        files = [dirpath]
        assert find_rpm_untracked(files) == [dirpath]

        # not existing files are ignored
        files = [NOFILE]
        assert find_rpm_untracked(files) == []

        # combinations should yield expected results too
        files = ["/tmp", dirpath, NOFILE]
        assert find_rpm_untracked(files) == [dirpath]
        # regardless the order
        files = [NOFILE, dirpath, "/tmp"]
        assert find_rpm_untracked(files) == [dirpath]
    finally:
        shutil.rmtree(dirpath)


def test_read_current_policy():
    with pytest.raises(StopActorExecutionError):
        assert read_current_policy(NOFILE)

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b'DEFAULT:SHA1')
        f.flush()
        assert read_current_policy(f.name) == "DEFAULT:SHA1"

        f.seek(0)
        f.write(b'  DEFAULT:SHA1   \n\n   ')
        f.flush()
        assert read_current_policy(f.name) == "DEFAULT:SHA1"


def test_read_policy_dirs(current_actor_context):
    # python2 compatibility :/
    dirpath = tempfile.mkdtemp()

    try:
        # empty
        files = read_policy_dirs([dirpath], CustomCryptoPolicy, ".pol")
        assert files == []

        # first policy module
        path1 = os.path.join(dirpath, "policy.mpol")
        with open(path1, "w") as f:
            f.write('test')
        files = read_policy_dirs([dirpath], CustomCryptoPolicy, ".pol")
        assert files == []
        files = read_policy_dirs([dirpath], CustomCryptoPolicyModule, ".mpol")
        assert files == [CustomCryptoPolicyModule(name="policy", path=path1)]

        # python2 compatibility :/
        dirpath2 = tempfile.mkdtemp()

        try:
            files = read_policy_dirs([dirpath], CustomCryptoPolicy, ".pol")
            assert files == []
            files = read_policy_dirs([dirpath, dirpath2], CustomCryptoPolicyModule, ".mpol")
            assert files == [CustomCryptoPolicyModule(name="policy", path=path1)]

            # first policy file
            path2 = os.path.join(dirpath2, "mypolicy.pol")
            with open(path2, "w") as f:
                f.write('test2')
            # second policy file
            path3 = os.path.join(dirpath2, "other.pol")
            with open(path3, "w") as f:
                f.write('test3')

            files = read_policy_dirs([dirpath, dirpath2], dict, ".pol")
            assert len(files) == 2
            assert dict(name="mypolicy", path=path2) in files
            assert dict(name="other", path=path3) in files
            files = read_policy_dirs([dirpath, dirpath2], CustomCryptoPolicyModule, ".mpol")
            assert files == [CustomCryptoPolicyModule(name="policy", path=path1)]
        finally:
            shutil.rmtree(dirpath2)

        files = read_policy_dirs([dirpath], CustomCryptoPolicy, ".pol")
        assert files == []
        files = read_policy_dirs([dirpath], CustomCryptoPolicyModule, ".mpol")
        assert files == [CustomCryptoPolicyModule(name="policy", path=path1)]
    finally:
        shutil.rmtree(dirpath)
