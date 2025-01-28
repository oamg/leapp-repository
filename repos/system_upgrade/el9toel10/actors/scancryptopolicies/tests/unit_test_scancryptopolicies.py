import os
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

    # the tempfile is not tracked by RPM
    with tempfile.NamedTemporaryFile(delete=False) as f:
        files = [f.name]
        assert find_rpm_untracked(files) == [f.name]

        # not existing files are ignored
        files = [NOFILE]
        assert find_rpm_untracked(files) == []

        # combinations should yield expected results too
        files = ["/tmp", f.name, NOFILE]
        assert find_rpm_untracked(files) == [f.name]
        # regardless the order
        files = [NOFILE, f.name, "/tmp"]
        assert find_rpm_untracked(files) == [f.name]


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
    with tempfile.TemporaryDirectory() as dir1:
        # empty
        files = read_policy_dirs([dir1], CustomCryptoPolicy, ".pol")
        assert files == []

        # first policy module
        path1 = os.path.join(dir1, "policy.mpol")
        with open(path1, "x") as f:
            f.write('test')
        files = read_policy_dirs([dir1], CustomCryptoPolicy, ".pol")
        assert files == []
        files = read_policy_dirs([dir1], CustomCryptoPolicyModule, ".mpol")
        assert files == [CustomCryptoPolicyModule(name="policy", path=path1)]

        with tempfile.TemporaryDirectory() as dir2:
            files = read_policy_dirs([dir1], CustomCryptoPolicy, ".pol")
            assert files == []
            files = read_policy_dirs([dir1, dir2], CustomCryptoPolicyModule, ".mpol")
            assert files == [CustomCryptoPolicyModule(name="policy", path=path1)]

            # first policy file
            path2 = os.path.join(dir2, "mypolicy.pol")
            with open(path2, "x") as f:
                f.write('test2')
            # second policy file
            path3 = os.path.join(dir2, "other.pol")
            with open(path3, "x") as f:
                f.write('test3')

            files = read_policy_dirs([dir1, dir2], dict, ".pol")
            assert len(files) == 2
            assert dict(name="mypolicy", path=path2) in files
            assert dict(name="other", path=path3) in files
            files = read_policy_dirs([dir1, dir2], CustomCryptoPolicyModule, ".mpol")
            assert files == [CustomCryptoPolicyModule(name="policy", path=path1)]

        files = read_policy_dirs([dir1], CustomCryptoPolicy, ".pol")
        assert files == []
        files = read_policy_dirs([dir1], CustomCryptoPolicyModule, ".mpol")
        assert files == [CustomCryptoPolicyModule(name="policy", path=path1)]
