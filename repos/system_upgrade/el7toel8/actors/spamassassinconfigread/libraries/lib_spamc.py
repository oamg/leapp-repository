import errno
import re

from leapp.libraries.common.spamassassinutils import SPAMC_CONFIG_FILE
from leapp.libraries.stdlib import api


def _remove_comments(content):
    return re.sub(r'^#.*$', '', content, flags=re.MULTILINE)


def _parse_spamc_ssl_argument(content):
    content = _remove_comments(content)
    res = None
    for match in re.finditer(r'(?<!\S)--ssl(\s+|=)(sslv3|tlsv1)(?!\S)', content):
        arg = match.group(2)
        if arg == 'tlsv1' or (arg == 'sslv3' and res is None):
            res = arg
    return res


def get_spamc_ssl_argument(read_func):
    """
    Extracts and returns the argument given to the --ssl option from the spamc
    configuration file. Returns None if the option is not specified or the config
    file does not exist.
    """
    try:
        content = read_func(SPAMC_CONFIG_FILE)
        return _parse_spamc_ssl_argument(content)
    except (IOError, OSError) as e:
        if e.errno != errno.ENOENT:
            api.current_logger().warning(
                'Failed to read spamc configuration file: %s' % e)
        return None
