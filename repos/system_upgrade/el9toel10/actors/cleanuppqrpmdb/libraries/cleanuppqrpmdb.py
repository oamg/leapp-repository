import os
import shutil

from leapp.libraries.common.config.version import matches_source_version
from leapp.libraries.stdlib import api

# The pqrpm leftover directory (the pqrpmdb is in it in lib/sysimage/rpm)
PQRPM_USR_DIR = '/usr/lib/pqrpm/'


def process():
    # pqrpm package, which includes the pqrpmdb can be installed on source
    # system >= 9.7 and < 10.0, however the entire implementation around PQC in
    # leapp is only active on 9.9 and 9.10 (see 4a70ee69) so also following
    # that here
    if not matches_source_version('>= 9.9', '< 10.0'):
        api.current_logger().debug(
            'Source system version is out of the >= 9.9, < 10.0 range, '
            'skipping pqrpm directory cleanup.'
        )
        return

    if not os.path.isdir(PQRPM_USR_DIR):
        api.current_logger().debug(
            'The pqrpm directory %s does not exist, nothing to clean up.',
            PQRPM_USR_DIR
        )
        return

    api.current_logger().info('Removing the pqrpm directory %s.', PQRPM_USR_DIR)
    try:
        shutil.rmtree(PQRPM_USR_DIR)
    except OSError as e:
        api.current_logger().warning(
            'Failed to remove the pqrpm directory %s: %s', PQRPM_USR_DIR, e
        )
