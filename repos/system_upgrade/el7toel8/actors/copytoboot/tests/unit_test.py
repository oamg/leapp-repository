import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import library
from leapp.libraries.stdlib import api
from leapp.models import BootContent

FILES_TO_COPY = {library.INITRAM_FILENAME: {'src_path': '/src/{}'.format(library.INITRAM_FILENAME),
                                            'dst_path': '/boot/{}'.format(library.INITRAM_FILENAME)},
                 library.KERNEL_FILENAME: {'src_path': '/src/{}'.format(library.KERNEL_FILENAME),
                                           'dst_path': '/boot/{}'.format(library.KERNEL_FILENAME)}}


class produce_mocked(object):
    def __call__(self, *model_instances):
        self.model_instances = model_instances


def test_copy_to_boot(monkeypatch):
    # Test that the actor produces the BootContent message
    def do_nothing(*args):
        pass
    monkeypatch.setattr(library, 'get_files_to_copy', do_nothing)
    monkeypatch.setattr(library, 'copy_files', do_nothing)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    library.copy_to_boot()

    assert type(api.produce.model_instances[0]) is BootContent


def test_get_files_to_copy(monkeypatch):
    # Test that the get_files_to_copy() returns an expected dict
    def get_src_filepath_mocked(filename):
        return '/src/{}'.format(filename)
    monkeypatch.setattr(library, 'get_src_filepath', get_src_filepath_mocked)

    def get_dst_filepath_mocked(filename):
        return '/boot/{}'.format(filename)
    monkeypatch.setattr(library, 'get_dst_filepath', get_dst_filepath_mocked)

    files_to_copy = library.get_files_to_copy()

    assert files_to_copy == FILES_TO_COPY


def test_get_src_filepath(monkeypatch):
    # Test that internal exception is raised if the source file for copying is not found
    def get_file_path_mocked(filename):
        return None
    monkeypatch.setattr(api, 'get_file_path', get_file_path_mocked)

    def files_paths_mocked():
        return ['/path']
    monkeypatch.setattr(api, 'files_paths', files_paths_mocked)

    with pytest.raises(StopActorExecutionError):
        library.get_src_filepath('filename')


def test_copy_files(monkeypatch):
    # Test that internal exception is raised if it's not possible to copy a file
    def copyfile_mocked(src, dst):
        raise IOError
    monkeypatch.setattr('shutil.copyfile', copyfile_mocked)

    with pytest.raises(StopActorExecutionError):
        library.copy_files(FILES_TO_COPY)
