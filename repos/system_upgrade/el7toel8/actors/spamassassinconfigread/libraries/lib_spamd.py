import errno
import os
import re

import leapp.libraries.common.spamassassinutils as lib
from leapp.libraries.stdlib import api


def spamassassin_service_overriden(listdir):
    file_name = os.path.basename(lib.SPAMASSASSIN_SERVICE_OVERRIDE)
    dir_path = os.path.dirname(lib.SPAMASSASSIN_SERVICE_OVERRIDE)
    try:
        return file_name in listdir(dir_path)
    except OSError as e:
        return e.errno != errno.ENOENT


def _parse_ssl_version(content):
    _, assignment, _ = lib.parse_sysconfig_spamassassin(content)
    if re.search(r'(?<![\w-])--ssl-version(=|\s+)sslv3(?![\w-])', assignment):
        return 'sslv3'
    if re.search(r'(?<![\w-])--ssl-version(=|\s+)tlsv1(?![\w-])', assignment):
        return 'tlsv1'
    return None


def get_spamd_ssl_version(read_func):
    """
    Extracts and returns the argument given to the --ssl-version option from
    the spamassassin sysconfig file. Returns None if the option is not specified
    or the file does not exist.
    """
    try:
        content = read_func(lib.SYSCONFIG_SPAMASSASSIN)
    except (IOError, OSError) as e:
        if e.errno != errno.ENOENT:
            api.current_logger().warning(
                'Failed to read spamassassin sysconfig file: %s' % e)
        return None
    return _parse_ssl_version(content)
