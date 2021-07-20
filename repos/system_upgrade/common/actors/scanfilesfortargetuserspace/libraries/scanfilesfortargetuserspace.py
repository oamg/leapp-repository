import os

from leapp.libraries.stdlib import api
from leapp.models import CopyFile, TargetUserSpacePreupgradeTasks

# Maps src location in the source system to the destination within the target system
FILES_TO_COPY_IF_PRESENT = {
    '/etc/hosts': '/etc/hosts'
}


def scan_files_to_copy():
    """
    Scans the source system and identifies files that should be copied into target userspace.

    When an item to be copied is identified a message :class:`CopyFile` is produced.
    """
    files_to_copy = []
    for src_path in FILES_TO_COPY_IF_PRESENT:
        if os.path.isfile(src_path):
            dst_path = FILES_TO_COPY_IF_PRESENT[src_path]
            files_to_copy.append(CopyFile(src=src_path, dst=dst_path))

    preupgrade_task = TargetUserSpacePreupgradeTasks(copy_files=files_to_copy)

    api.produce(preupgrade_task)
