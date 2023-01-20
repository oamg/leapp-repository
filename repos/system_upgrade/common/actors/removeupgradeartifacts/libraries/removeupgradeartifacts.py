import os

from leapp.libraries.stdlib import api, CalledProcessError, run

UPGRADE_ARTIFACTS_DIR = '/root/tmp_leapp_py3/'


def process():
    if os.path.exists(UPGRADE_ARTIFACTS_DIR):
        api.current_logger().debug(
                "Removing leftover upgrade artifacts dir: {} ".format(UPGRADE_ARTIFACTS_DIR))

        try:
            run(['rm', '-rf', UPGRADE_ARTIFACTS_DIR])
        except (CalledProcessError, OSError) as e:
            api.current_logger().debug(
                    'Failed to remove leftover upgrade artifacts dir: {}'.format(e))
