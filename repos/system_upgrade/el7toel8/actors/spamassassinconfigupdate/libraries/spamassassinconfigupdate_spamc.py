import re

from leapp.libraries.common.spamassassinutils import SPAMC_CONFIG_FILE
from leapp.libraries.stdlib import api


def _rewrite_spamc_config(content):
    res_lines = []
    read_ssl_option = False
    for line in content.split('\n'):
        if line.startswith('#'):
            res_lines.append(line)
            continue
        if read_ssl_option:
            line = re.sub(r'^\s*(sslv3|tlsv1)', '', line)
            read_ssl_option = False
        if re.search(r'(?<!\S)--ssl\s*$', line):
            read_ssl_option = True
        line = re.sub(r'(?<!\S)--ssl(\s+|=)(sslv3|tlsv1)(?!\S)', '--ssl', line)
        res_lines.append(line)
    res = '\n'.join(res_lines)
    return res


def migrate_spamc_config(facts, fileops, backup_func):
    """
    Removes arguments given to the --ssl option in the spamc config file.
    The file is backed up beforehand.
    """
    if facts.spamc_ssl_argument is None:
        api.current_logger().info('There is nothing to migrate in the spamc configuration file')
        return
    try:
        backup_path = backup_func(SPAMC_CONFIG_FILE)
        api.current_logger().info('spamc configuration file backup created at %s.'
                                  % backup_path)
    except (OSError, IOError) as e:
        api.current_logger().warning(
            'spamc configuration file migration will not be performed. Failed to create backup: %s' % e)
        return
    try:
        content = fileops.read(SPAMC_CONFIG_FILE)
        new_content = _rewrite_spamc_config(content)
        fileops.write(SPAMC_CONFIG_FILE, new_content)
    except (OSError, IOError) as e:
        api.current_logger().warning('Failed to migrate spamc configuration file: %s' % e)
