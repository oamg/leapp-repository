import shutil
from os import path

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import BootContent

INITRAM_FILENAME = 'initramfs-upgrade.x86_64.img'
KERNEL_FILENAME = 'vmlinuz-upgrade.x86_64'


def copy_to_boot():
    files_to_copy = get_files_to_copy()
    copy_files(files_to_copy)
    message_copied_files()


def get_files_to_copy():
    files_to_copy = {}
    for filename in KERNEL_FILENAME, INITRAM_FILENAME:
        files_to_copy[filename] = {'src_path': get_src_filepath(filename), 'dst_path': get_dst_filepath(filename)}
    return files_to_copy


def get_src_filepath(filename):
    src_filepath = api.get_file_path(filename)
    if src_filepath is None:
        raise StopActorExecutionError('Could not find {0} in the following paths: {1}'
                                      .format(filename, ' '.join(api.files_paths())),
                                      details={'hint': 'You may want to try to reinstall'
                                                       ' the "leapp-repository" package'})
    return src_filepath


def get_dst_filepath(filename):
    return path.join('/boot', filename)


def copy_files(files_to_copy):
    for filename in files_to_copy.keys():
        try:
            shutil.copyfile(files_to_copy[filename]['src_path'], files_to_copy[filename]['dst_path'])
        except IOError as err:
            raise StopActorExecutionError('Could not copy {0} to /boot'.format(files_to_copy[filename]['src_path']),
                                          details={'details': str(err)})


def message_copied_files():
    """Let the other actors know what files we've stored on /boot."""
    api.produce(BootContent(kernel_path=get_dst_filepath(KERNEL_FILENAME),
                            initram_path=get_dst_filepath(INITRAM_FILENAME)))
