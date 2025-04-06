import os

from leapp.libraries.stdlib import api
from leapp.models import CopyFile, TargetUserSpacePreupgradeTasks


class FileToCopy:
    """
    A file to be copied into target userspace

    Also see DirToCopy
    """
    def __init__(self, src_path, dst_path=None, fallback=None):
        """
        Initialize a new FileToCopy

        The file at src_path on the source system is to be copied to the
        dst_path in the target userspace. The fallback argument allows creating
        a chain of fallback files to try if the original file doesn't
        exist(practically a linked list).

        :param src_path: The path to the file on the source system
        :param dst_path: The path in the target userspace, or src_path if not given
        :param fallback: A file to try next if src_path doesn't exist
        """
        self.src_path = src_path
        self.dst_path = dst_path if dst_path else src_path
        self.fallback = fallback

    def check_filetype(self):
        return os.path.isfile(self.src_path)


class DirToCopy(FileToCopy):
    """
    A directory to be copied into target userspace

    Also see FileToCopy
    """
    def check_filetype(self):
        return os.path.isdir(self.src_path)


# list of files and directories to copy into target userspace
FILES_TO_COPY_IF_PRESENT = [
    FileToCopy('/etc/hosts'),
    # the fallback usually goes to /etc/mdadm/mdadm.conf, however the /etc/mdadm dir
    # doesn't exist in the target userspace and the targetuserspacecreator expects
    # the destination dir to exist, so let's copy to /etc/. dracut also copies it there
    FileToCopy('/etc/mdadm.conf', fallback=FileToCopy('/etc/mdadm/mdadm.conf', '/etc/mdadm.conf')),
    # copy to /etc/mdadm.conf.d/, dracut only copies this one into initramfs and doesn't check the alternate one
    DirToCopy('/etc/mdadm.conf.d/', fallback=FileToCopy('/etc/mdadm/mdadm.conf.d/', '/etc/mdadm.conf.d/'))
]


def _scan_file_to_copy(file):
    """
    Scan the source system and identify file that should be copied into target userspace.

    If the file doesn't exists or isn't of the right type it's fallbacks are searched, if set.

    :return: The found file or None
    :rtype: CopyFile | None
    """
    tmp = file
    while tmp and not tmp.check_filetype():
        tmp = tmp.fallback

    if not tmp:
        api.current_logger().warning(
                "File {} and its fallbacks do not exist or are not a correct filetype".format(file.src_path))
        return None

    return CopyFile(src=tmp.src_path, dst=tmp.dst_path)


def scan_files_to_copy():
    """
    Scans the source system and identifies files that should be copied into target userspace.

    When an item to be copied is identified a message :class:`CopyFile` is produced.
    """
    files_to_copy = []
    for file in FILES_TO_COPY_IF_PRESENT:
        file_to_copy = _scan_file_to_copy(file)
        if file_to_copy:
            files_to_copy.append(file_to_copy)

    preupgrade_task = TargetUserSpacePreupgradeTasks(copy_files=files_to_copy)

    api.produce(preupgrade_task)
