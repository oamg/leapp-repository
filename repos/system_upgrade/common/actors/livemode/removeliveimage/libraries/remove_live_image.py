import os

from leapp.libraries.stdlib import api
from leapp.models import LiveModeArtifacts, LiveModeConfig


def remove_live_image():
    livemode = next(api.consume(LiveModeConfig), None)
    if not livemode or not livemode.is_enabled:
        return

    artifacts = next(api.consume(LiveModeArtifacts), None)

    if not artifacts:
        # Livemode is enabled, but we have received no artifacts - this should not happen.
        # Anyway, it is futile to sabotage the upgrade this late (after the upgrade transaction)
        error_descr = ('Livemode is enabled, but there is no LiveModeArtifacts message. '
                       'Cannot delete squashfs image (location is unknown)')
        api.current_logger().error(error_descr)
        return

    try:
        os.unlink(artifacts.squashfs_path)
    except OSError as error:
        api.current_logger().warning('Failed to remove %s with error: %s', artifacts.squashfs, error)
