import os
import shutil
import tempfile

from leapp.libraries.actor import scanblacklistca
from leapp.libraries.actor.scanblacklistca import _get_files
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import BlackListCA, BlackListError

CURDIR = os.path.dirname(os.path.abspath(__file__))
TESTCERT = "badca.cert"
TESTLINK = "linkca.cert"
SUBDIR = "casdir"


class MockedGetFiles(object):
    def __init__(self, files=None, error=None):
        self.called = 0
        self.files = files
        self.error = error
        self.targets = []

    def __call__(self, directory):
        self.targets.append(directory)
        self.called += 1
        if self.error:
            pret = {'signal': 0, 'exit_code': 0xff, 'pid': 0}
            raise CalledProcessError(command="dummy", result=pret, message=self.error)
        ret = []
        for f in self.files:
            ret.append(os.path.join(directory, f))
        return ret


class MockedGetDirs(object):
    def __init__(self, dirs):
        self.called = 0
        self.dirs = dirs

    def __call__(self):
        self.called += 1
        return self.dirs


# make sure get_files is not called if the directory doesn't exist
def test_non_existant_directory(monkeypatch):
    mocked_files = MockedGetFiles()
    monkeypatch.setattr(os.path, 'exists', lambda dummy: False)
    monkeypatch.setattr(scanblacklistca, '_get_files', mocked_files)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(scanblacklistca, 'run', lambda dummy: dummy)
    scanblacklistca.process()
    assert not mocked_files.called


# unit tests for get_files
def test_get_files(current_actor_context):
    # empty directory
    with tempfile.TemporaryDirectory() as srcdir:
        srcfile = os.path.join(CURDIR, "files", TESTCERT)
        files = _get_files(srcdir)
        assert len(files) == 0
        # single file
        shutil.copy(srcfile, srcdir)
        # make sure we can find certs in the directory
        files = _get_files(srcdir)
        assert len(files) == 1
        assert files[0] == os.path.join(srcdir, TESTCERT)
        # file and symbolic link
        os.symlink(srcfile, os.path.join(srcdir, TESTLINK))
        # make sure we can find certs and links together in the directory
        files = _get_files(srcdir)
        assert len(files) == 2
        assert os.path.join(srcdir, TESTCERT) in files
        assert os.path.join(srcdir, TESTLINK) in files

    # single symbolic link
    with tempfile.TemporaryDirectory() as srcdir:
        os.symlink(srcfile, os.path.join(srcdir, TESTLINK))
        # make sure we can find a solo link in the directory
        files = _get_files(srcdir)
        assert len(files) == 1
        assert files[0] == os.path.join(srcdir, TESTLINK)

    # empty subdirectory
    with tempfile.TemporaryDirectory() as srcdir:
        os.mkdir(os.path.join(srcdir, SUBDIR))
        files = _get_files(srcdir)
        assert len(files) == 0
        # make sure we can find certs in the directory
        shutil.copy(os.path.join(CURDIR, "files", TESTCERT), os.path.join(srcdir, SUBDIR))
        files = _get_files(srcdir)
        assert len(files) == 1
        assert files[0] == os.path.join(srcdir, SUBDIR, TESTCERT)


def test_messages(monkeypatch):
    with tempfile.TemporaryDirectory() as srcdir:
        with tempfile.TemporaryDirectory() as targdir:
            mocked_files = MockedGetFiles(files=[TESTCERT, TESTLINK])
            mocked_dirs = MockedGetDirs(dirs={srcdir: targdir})
            monkeypatch.setattr(scanblacklistca, '_get_files', mocked_files)
            monkeypatch.setattr(scanblacklistca, '_get_dirs', mocked_dirs)
            monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
            monkeypatch.setattr(api, "produce", produce_mocked())
            scanblacklistca.process()
            assert mocked_files.called == 1
            assert len(mocked_files.targets) == 1
            assert mocked_files.targets[0] == srcdir
            assert api.produce.called == 2
            assert len(api.produce.model_instances) == 2
            assert isinstance(api.produce.model_instances[0], BlackListCA)
            assert isinstance(api.produce.model_instances[1], BlackListCA)
            assert api.produce.model_instances[0].sourceDir == srcdir
            assert api.produce.model_instances[0].source == os.path.join(srcdir, TESTCERT)
            assert api.produce.model_instances[0].target == os.path.join(targdir, TESTCERT)
            assert api.produce.model_instances[0].targetDir == targdir
            assert api.produce.model_instances[1].sourceDir == srcdir
            assert api.produce.model_instances[1].source == os.path.join(srcdir, TESTLINK)
            assert api.produce.model_instances[1].target == os.path.join(targdir, TESTLINK)
            assert api.produce.model_instances[1].targetDir == targdir


def test_error(monkeypatch):
    with tempfile.TemporaryDirectory() as srcdir:
        with tempfile.TemporaryDirectory() as targdir:
            error = "get files failed"
            mocked_files = MockedGetFiles(error=error)
            mocked_dirs = MockedGetDirs(dirs={srcdir: targdir})
            monkeypatch.setattr(scanblacklistca, '_get_files', mocked_files)
            monkeypatch.setattr(scanblacklistca, '_get_dirs', mocked_dirs)
            monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
            monkeypatch.setattr(api, "produce", produce_mocked())
            scanblacklistca.process()
            assert mocked_files.called == 1
            assert api.produce.called == 1
            assert len(api.produce.model_instances) == 1
            assert isinstance(api.produce.model_instances[0], BlackListError)
            assert api.produce.model_instances[0].sourceDir == srcdir
            assert api.produce.model_instances[0].targetDir == targdir
            assert api.produce.model_instances[0].error == error
