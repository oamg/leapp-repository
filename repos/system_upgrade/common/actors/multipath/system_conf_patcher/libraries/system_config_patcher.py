import os
import shutil

from leapp.libraries.stdlib import api
from leapp.models import TargetUserSpaceInfo, UpdatedMultipathConfig


def patch_system_configs():
    modified_configs_used_during_upgrade = api.consume(UpdatedMultipathConfig)
    target_uspace_info = next(api.consume(TargetUserSpaceInfo))

    for modified_config in modified_configs_used_during_upgrade:
        rootless_path = modified_config.path.lstrip('/')
        uspace_location = os.path.join(target_uspace_info.path, rootless_path)
        system_location = modified_config.path

        api.current_logger().debug(
            'Copying modified multipath config {} from userspace to {}.'.format(
                uspace_location, system_location
            )
        )

        shutil.copy(uspace_location, system_location)
