import glob
import os

from leapp.libraries.stdlib import api


def remove_sssd_cache_files(config):
    """
    Remove all SSSD cache files.
    """
    if not config:
        return

    for cache_file in glob.glob('/var/lib/sss/db/*.ldb'):
        try:
            api.current_logger().info('Pruning SSSD cache file {}'.format(cache_file))
            os.remove(cache_file)
        except OSError:
            api.current_logger().warning('Failed to remove cache file: %s', cache_file)
