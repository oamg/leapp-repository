import os
import shutil

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import mount_unit_generator
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import TargetUserSpaceInfo, UpgradeInitramfsTasks


def test_run_systemd_fstab_generator_successful_generation(monkeypatch):
    """Test successful mount unit generation."""

    output_dir = '/tmp/test_output'
    expected_cmd = [
        '/usr/lib/systemd/system-generators/systemd-fstab-generator',
        output_dir,
        output_dir,
        output_dir
    ]

    def mock_run(command):
        assert command == expected_cmd

        return {
            "stdout": "",
            "stderr": "",
            "exit_code": 0,
        }

    monkeypatch.setattr(mount_unit_generator, 'run', mock_run)
    mount_unit_generator.run_systemd_fstab_generator(output_dir)


def test_run_systemd_fstab_generator_failure(monkeypatch):
    """Test handling of systemd-fstab-generator failure."""
    output_dir = '/tmp/test_output'
    expected_cmd = [
        '/usr/lib/systemd/system-generators/systemd-fstab-generator',
        output_dir,
        output_dir,
        output_dir
    ]

    def mock_run(command):
        assert command == expected_cmd
        raise CalledProcessError(message='Generator failed', command=['test'], result={'exit_code': 1})

    monkeypatch.setattr(mount_unit_generator, 'run', mock_run)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    with pytest.raises(StopActorExecutionError):
        mount_unit_generator.run_systemd_fstab_generator(output_dir)


def test_prefix_mount_unit_with_sysroot(monkeypatch):
    """Test prefixing a single mount unit with /sysroot."""
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    input_content = [
        "[Unit]\n",
        "Description=Test Mount\n",
        "[Mount]\n",
        "Where=/home\n",
        "What=/dev/sda1\n"
    ]

    expected_output_lines = [
        "[Unit]",
        "Description=Test Mount",
        "[Mount]",
        "Where=/sysroot/home",
        "What=/dev/sda1"
    ]

    def mock_read_unit_file_lines(unit_file_path):
        return input_content

    def mock_write_unit_file_lines(unit_file_path, lines):
        assert unit_file_path == '/test/output.mount'
        assert lines == expected_output_lines

    monkeypatch.setattr(mount_unit_generator, '_read_unit_file_lines', mock_read_unit_file_lines)
    monkeypatch.setattr(mount_unit_generator, '_write_unit_file_lines', mock_write_unit_file_lines)

    mount_unit_generator._prefix_mount_unit_with_sysroot(
        '/test/input.mount',
        '/test/output.mount'
    )


def test_prefix_all_mount_units_with_sysroot(monkeypatch):
    """Test prefixing all mount units in a directory."""

    expected_changes = {
        '/test/dir/home.mount': {
            'new_unit_destination': '/test/dir/sysroot-home.mount',
            'should_be_deleted': True,
            'deleted': False,
        },
        '/test/dir/var.mount': {
            'new_unit_destination': '/test/dir/sysroot-var.mount',
            'should_be_deleted': True,
            'deleted': False,
        },
        '/test/dir/not-a-mount.service': {
            'new_unit_destination': None,
            'should_be_deleted': False,
            'deleted': False,
        }
    }

    def mock_listdir(dir_path):
        return ['home.mount', 'var.mount', 'not-a-mount.service']

    def mock_delete_file(file_path):
        assert file_path in expected_changes
        expected_changes[file_path]['deleted'] = True

    def mock_prefix(unit_file_path, new_unit_destination):
        assert expected_changes[unit_file_path]['new_unit_destination'] == new_unit_destination

    monkeypatch.setattr('os.listdir', mock_listdir)
    monkeypatch.setattr(mount_unit_generator, '_delete_file', mock_delete_file)
    monkeypatch.setattr(mount_unit_generator, '_prefix_mount_unit_with_sysroot', mock_prefix)

    mount_unit_generator.prefix_all_mount_units_with_sysroot('/test/dir')

    for original_mount_unit_location in expected_changes:
        should_be_deleted = expected_changes[original_mount_unit_location]['should_be_deleted']
        was_deleted = expected_changes[original_mount_unit_location]['deleted']
        assert should_be_deleted == was_deleted


@pytest.mark.parametrize('dirname', (
    'local-fs.target.requires',
    'local-fs.target.wants',
    'local-fs-pre.target.requires',
    'local-fs-pre.target.wants',
    'remote-fs.target.requires',
    'remote-fs.target.wants',
    'remote-fs-pre.target.requires',
    'remote-fs-pre.target.wants',
))
def test_fix_symlinks_in_dir(monkeypatch, dirname):
    """Test fixing local-fs.target.requires symlinks."""

    DIR_PATH = os.path.join('/test/dir/', dirname)

    def mock_rmtree(dir_path):
        assert dir_path == DIR_PATH

    def mock_mkdir(dir_path):
        assert dir_path == DIR_PATH

    def mock_listdir(dir_path):
        return ['sysroot-home.mount', 'sysroot-var.mount', 'not-a-mount.service']

    def mock_os_path_exist(dir_path):
        assert dir_path == DIR_PATH
        return dir_path == DIR_PATH

    expected_calls = [
        ['ln', '-s', '../sysroot-home.mount', os.path.join(DIR_PATH, 'sysroot-home.mount')],
        ['ln', '-s', '../sysroot-var.mount', os.path.join(DIR_PATH, 'sysroot-var.mount')]
    ]
    call_count = 0

    def mock_run(command):
        nonlocal call_count
        assert command in expected_calls
        call_count += 1
        return {
            "stdout": "",
            "stderr": "",
            "exit_code": 0,
        }

    monkeypatch.setattr('shutil.rmtree', mock_rmtree)
    monkeypatch.setattr('os.mkdir', mock_mkdir)
    monkeypatch.setattr('os.listdir', mock_listdir)
    monkeypatch.setattr('os.path.exists', mock_os_path_exist)
    monkeypatch.setattr(mount_unit_generator, 'run', mock_run)

    mount_unit_generator._fix_symlinks_in_dir('/test/dir', dirname)


# Test the copy_units_into_system_location function
def test_copy_units_mixed_content(monkeypatch):
    """Test copying units with mixed files and directories."""

    def mock_walk(dir_path):
        tuples_to_yield = [
            ('/source/dir', ['local-fs.target.requires'], ['unit1.mount', 'unit2.mount']),
            ('/source/dir/local-fs.target.requires', [], ['unit1.mount', 'unit2.mount']),
        ]
        yield from tuples_to_yield

    def mock_isdir(path):
        return 'local-fs.target.requires' in path

    def _make_couple(sub_path):
        return (
            os.path.join('/source/dir/', sub_path),
            os.path.join('/container/usr/lib/systemd/system/', sub_path)
        )

    def mock_copy2(src, dst, follow_symlinks=True):
        valid_combinations = [
            _make_couple('unit1.mount'),
            _make_couple('unit2.mount'),
            _make_couple('local-fs.target.requires/unit1.mount'),
            _make_couple('local-fs.target.requires/unit2.mount'),
        ]
        assert not follow_symlinks
        assert (src, dst) in valid_combinations

    def mock_islink(file_path):
        return file_path == '/container/usr/lib/systemd/system/local-fs.target.requires/unit2.mount'

    class MockedDeleteFile:
        def __init__(self):
            self.removal_called = False

        def __call__(self, file_path):
            assert file_path == '/container/usr/lib/systemd/system/local-fs.target.requires/unit2.mount'
            self.removal_called = True

    def mock_makedirs(dst_dir, mode=0o777, exist_ok=False):
        assert exist_ok
        assert mode == 0o755

        allowed_paths = [
            '/container/usr/lib/systemd/system',
            '/container/usr/lib/systemd/system/local-fs.target.requires'
        ]
        assert dst_dir.rstrip('/') in allowed_paths

    monkeypatch.setattr(os, 'walk', mock_walk)
    monkeypatch.setattr(os, 'makedirs', mock_makedirs)
    monkeypatch.setattr(os.path, 'isdir', mock_isdir)
    monkeypatch.setattr(os.path, 'islink', mock_islink)
    monkeypatch.setattr(mount_unit_generator, '_delete_file', MockedDeleteFile())
    monkeypatch.setattr(shutil, 'copy2', mock_copy2)

    class MockedContainerContext:
        def __init__(self):
            self.base_dir = '/container'

        def full_path(self, path):
            return os.path.join('/container', path.lstrip('/'))

    mock_container = MockedContainerContext()

    files = mount_unit_generator.copy_units_into_system_location(
        mock_container, '/source/dir'
    )

    expected_files = [
        '/usr/lib/systemd/system/unit1.mount',
        '/usr/lib/systemd/system/unit2.mount',
        '/usr/lib/systemd/system/local-fs.target.requires/unit1.mount',
        '/usr/lib/systemd/system/local-fs.target.requires/unit2.mount',
    ]
    assert sorted(files) == sorted(expected_files)
    assert mount_unit_generator._delete_file.removal_called
