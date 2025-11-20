import shutil

from leapp.libraries.stdlib import api
from leapp.models import UpdatedMultipathConfig


def patch_system_configs():
    modified_configs_used_during_upgrade = api.consume(UpdatedMultipathConfig)

    for modified_config in modified_configs_used_during_upgrade:
        api.current_logger().debug(
            'Copying modified multipath config {} to {}.'.format(
                modified_config.updated_config_location,
                modified_config.target_path
            )
        )

        shutil.copy(modified_config.updated_config_location, modified_config.target_path)
