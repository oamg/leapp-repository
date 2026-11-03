import os
import shutil

from leapp.libraries.common.config.version import matches_source_version
from leapp.libraries.stdlib import api

# The pqrpm RPM DB is a directory, not a regular file.
PQRPM_DB_DIR = '/usr/lib/pqrpm/lib/sysimage/rpm'


def process():
    # The pqrpm DB and its PQC verification mechanism are only set up on
    # source systems >= 9.9 (where the 'sq' utility is available), so there
    # is nothing to clean up on older systems.
    if not matches_source_version('>= 9.9', '< 10.0'):
        api.current_logger().debug(
            'Source system version is out of the >= 9.9, < 10.0 range, '
            'skipping pqrpmdb cleanup.'
        )
        return

    if not os.path.isdir(PQRPM_DB_DIR):
        api.current_logger().debug(
            'The pqrpm DB directory %s does not exist, nothing to clean up.',
            PQRPM_DB_DIR
        )
        return

    api.current_logger().info('Removing the pqrpmdb directory %s.', PQRPM_DB_DIR)
    try:
        shutil.rmtree(PQRPM_DB_DIR)
    except OSError as e:
        api.current_logger().warning(
            'Failed to remove the pqrpmdb directory %s: %s', PQRPM_DB_DIR, e
        )
