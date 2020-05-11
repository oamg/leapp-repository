import os
import shutil
import stat
import tempfile

from leapp.libraries.actor.spamassassinconfigupdate_backup import backup_file


def test_backup_file():
    tmpdir = tempfile.mkdtemp()
    try:
        file_path = os.path.join(tmpdir, 'foo-bar')
        content = 'test content\n'
        with open(file_path, 'w') as f:
            f.write(content)

        backup_path = backup_file(file_path)

        assert os.path.basename(backup_path) == 'foo-bar.leapp-backup'
        assert os.path.dirname(backup_path) == tmpdir
        assert len(os.listdir(tmpdir)) == 2
        st = os.stat(backup_path)
        assert stat.S_IMODE(st.st_mode) == (stat.S_IRUSR | stat.S_IWUSR)
        with open(backup_path, 'r') as f:
            backup_content = f.read()
        assert backup_content == content
        with open(file_path, 'r') as f:
            orig_content = f.read()
        assert orig_content == content
    finally:
        shutil.rmtree(tmpdir)


def test_backup_file_target_exists():
    tmpdir = tempfile.mkdtemp()
    try:
        file_path = os.path.join(tmpdir, 'foo-bar')
        primary_target_path = '%s.leapp-backup' % file_path
        primary_target_content = 'do not overwrite me'
        content = 'test_content\n'
        with open(file_path, 'w') as f:
            f.write(content)
        with open(primary_target_path, 'w') as f:
            f.write(primary_target_content)

        backup_path = backup_file(file_path)

        assert os.path.basename(backup_path).startswith('foo-bar.leapp-backup.')
        assert os.path.dirname(backup_path) == tmpdir
        assert len(os.listdir(tmpdir)) == 3
        st = os.stat(backup_path)
        assert stat.S_IMODE(st.st_mode) == (stat.S_IRUSR | stat.S_IWUSR)
        with open(backup_path, 'r') as f:
            assert f.read() == content
        with open(primary_target_path, 'r') as f:
            assert f.read() == primary_target_content
    finally:
        shutil.rmtree(tmpdir)
