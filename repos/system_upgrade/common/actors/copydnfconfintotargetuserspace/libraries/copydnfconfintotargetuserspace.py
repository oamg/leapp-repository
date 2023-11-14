import os

from leapp.libraries.stdlib import api
from leapp.models import CopyFile, TargetUserSpacePreupgradeTasks


def process():
    src = "/etc/dnf/dnf.conf"
    if os.path.exists("/etc/leapp/files/dnf.conf"):
        src = "/etc/leapp/files/dnf.conf"

    api.current_logger().debug(
        "Copying dnf.conf at {} to the target userspace".format(src)
    )
    api.produce(
        TargetUserSpacePreupgradeTasks(
            copy_files=[CopyFile(src=src, dst="/etc/dnf/dnf.conf")]
        )
    )
