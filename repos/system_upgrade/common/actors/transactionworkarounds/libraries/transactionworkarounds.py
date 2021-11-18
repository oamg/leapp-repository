import os

from leapp.libraries.stdlib import api
from leapp.models import RpmTransactionTasks


def process():
    location = api.get_folder_path('bundled-rpms')
    local_rpms = []
    for name in os.listdir(location):
        if name.endswith('.rpm'):
            # It is important to put here the realpath to the files here, because
            # symlinks cannot be resolved properly inside of the target userspace since they use the /installroot
            # mount target
            local_rpms.append(os.path.realpath(os.path.join(location, name)))
    if local_rpms:
        api.produce(RpmTransactionTasks(local_rpms=local_rpms))
