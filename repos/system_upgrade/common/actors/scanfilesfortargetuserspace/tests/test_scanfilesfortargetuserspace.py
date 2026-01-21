import os

import pytest

from leapp.libraries.actor import scanfilesfortargetuserspace
from leapp.libraries.actor.scanfilesfortargetuserspace import DirToCopy, FileToCopy
from leapp.libraries.common.testutils import produce_mocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import CopyFile


def _do_files_to_copy_contain_entry(copy_files, file_to_copy):
    """Searches the files to be copied for an entry with src field that matches the given src."""
    for copy_file in copy_files:
        if (
            copy_file.src == file_to_copy.src_path
            and copy_file.dst == file_to_copy.dst_path
        ):
            return True
    return False


@pytest.mark.parametrize(
    "files",
    (
        [],
        [FileToCopy("/etc/file")],
        [
            FileToCopy("/etc/fileA"),
            FileToCopy("/etc/abcd/file", "/etc/1234/file"),
            DirToCopy("/etc/dirA/dirB/dirC/", fallback=DirToCopy("/fallback/dir")),
            DirToCopy("/root_level_dir", "/different/target/dir"),
        ],
    ),
)
def test_copyfiles_produced(monkeypatch, files):
    """
    Test that CopyFile models are correctly produced for all files to copy
    """
    scanfilesfortargetuserspace.FILES_TO_COPY_IF_PRESENT = files

    def _scan_file_to_copy_mocked(file):
        return CopyFile(src=file.src_path, dst=file.dst_path)

    actor_produces = produce_mocked()

    monkeypatch.setattr(
        scanfilesfortargetuserspace, "_scan_file_to_copy", _scan_file_to_copy_mocked
    )
    monkeypatch.setattr(api, "produce", actor_produces)

    scanfilesfortargetuserspace.scan_files_to_copy()

    fail_msg = "Produced unexpected number of messages."
    assert len(actor_produces.model_instances) == 1, fail_msg

    preupgrade_task_msg = actor_produces.model_instances[0]
    assert len(preupgrade_task_msg.copy_files) == len(files)

    for file in files:
        assert _do_files_to_copy_contain_entry(preupgrade_task_msg.copy_files, file)

    fail_msg = "Produced message contains rpms to be installed,"
    "however only copy files field should be populated."
    assert not preupgrade_task_msg.install_rpms, fail_msg


TEST_FILE_PATH = "/etc/file"
TEST_DIR_PATH = "/etc/dir"


@pytest.mark.parametrize("file_to_copy", (FileToCopy(TEST_FILE_PATH), DirToCopy(TEST_DIR_PATH)))
def test_copy_present(monkeypatch, file_to_copy):
    """Test that file to copy is found if present"""
    monkeypatch.setattr(os.path, "isdir", lambda f: f == TEST_DIR_PATH)
    monkeypatch.setattr(os.path, "isfile", lambda f: f == TEST_FILE_PATH)

    copy_file = scanfilesfortargetuserspace._scan_file_to_copy(file_to_copy)

    assert copy_file
    assert _do_files_to_copy_contain_entry([copy_file], file_to_copy)


@pytest.mark.parametrize(
    "file_to_copy",
    [
        FileToCopy("/etc/hosts"),
        DirToCopy("/etc/dnf"),
        FileToCopy("/etc/fileA", fallback=FileToCopy("/etc/fileB")),
    ],
)
def test_copy_missing(monkeypatch, file_to_copy):
    """Test that no file is found and returned if it isn't present"""
    monkeypatch.setattr(os.path, "isfile", lambda _: False)
    monkeypatch.setattr(os.path, "isdir", lambda _: False)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    copy_file = scanfilesfortargetuserspace._scan_file_to_copy(file_to_copy)
    assert not copy_file, "Should return None for a missing file"

    assert len(api.current_logger.warnmsg) == 1
    assert file_to_copy.src_path in api.current_logger.warnmsg[0]


def test_copy_missing_with_fallback(monkeypatch):
    """Test that fallback is found and returned if the original file is not present"""
    ORIG = "/etc/mdadm.conf"
    FALLBACK = "/etc/mdadm/mdadm.conf"

    monkeypatch.setattr(os.path, "isfile", lambda f: f == FALLBACK)

    fallback_file = FileToCopy(FALLBACK)
    file_to_scan = FileToCopy(ORIG, fallback=fallback_file)
    copy_file = scanfilesfortargetuserspace._scan_file_to_copy(file_to_scan)

    assert copy_file
    assert copy_file.src == FALLBACK
    assert copy_file.dst == FALLBACK
