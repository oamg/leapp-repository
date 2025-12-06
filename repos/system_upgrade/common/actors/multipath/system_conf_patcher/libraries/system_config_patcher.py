import shutil

from leapp.libraries.stdlib import api
from leapp.models import MultipathConfigUpdatesInfo


def patch_system_configs():
    for config_updates in api.consume(MultipathConfigUpdatesInfo):
        for modified_config in config_updates.updates:
            api.current_logger().debug(
                'Copying modified multipath config {} to {}.'.format(
                    modified_config.updated_config_location,
                    modified_config.target_path
                )
            )

            shutil.copy(modified_config.updated_config_location, modified_config.target_path)
