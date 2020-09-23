import errno
import re

import leapp.libraries.common.spamassassinutils as utils
from leapp.libraries.stdlib import api


def _drop_ssl_version(value):
    regex = r'(?<![\w-])--ssl-version(=|\s+)(sslv3|tlsv1)(?![\w-])'
    if not re.search(r'(?<![\w-])--ssl(?![\w-])', value):
        value = re.sub(regex, '--ssl', value, count=1)
    return re.sub(regex, '', value)


def _drop_daemonize_option(value):
    shortopts = utils.SPAMD_SHORTOPTS_NOARG
    value = re.sub(r'(?<![\w-])-d+(?![\w-])',
                   r'', value)
    while True:
        value, nsubs = re.subn(r'(?<![\w-])(-[' + shortopts + ']*)d',
                               r'\1', value)
        if nsubs == 0:
            break
    return re.sub(r'(?<![\w-])--daemonize(?![\w-])', '', value)


def _rewrite_spamd_option(content, ops):
    pre_assignment, assignment, post_assignment = \
        utils.parse_sysconfig_spamassassin(content)
    if assignment:
        value = re.sub(r'^\s*' + utils.SYSCONFIG_VARIABLE + r'\s*=(.*)$',
                       r'\1', assignment)
        for op in ops:
            value = op(value)
        assignment = utils.SYSCONFIG_VARIABLE + '=' + value
    res = '\n'.join(filter(None, (pre_assignment, assignment, post_assignment)))
    if res and not res.endswith('\n'):
        res += '\n'
    return res


def _rewrite_spamd_config(facts, content):
    ops = []
    if facts.spamd_ssl_version:
        ops.append(_drop_ssl_version)
    if not facts.service_overriden:
        ops.append(_drop_daemonize_option)
    return _rewrite_spamd_option(content, ops) if ops else content


def migrate_spamd_config(facts, fileops, backup_func):
    """
    Removes --ssl-version and -d/--daemonize options from the spamassassin
    sysconfig file. The file is backed up beforehand.
    """
    nothing_to_migrate_msg = 'There is nothing to migrate in the spamd configuration file'
    if facts.service_overriden and not facts.spamd_ssl_version:
        api.current_logger().info(nothing_to_migrate_msg)
        return
    try:
        content = fileops.read(utils.SYSCONFIG_SPAMASSASSIN)
    except (OSError, IOError) as e:
        if e.errno == errno.ENOENT:
            api.current_logger().info(nothing_to_migrate_msg)
        else:
            api.current_logger().warning('Failed to read spamd configuration file: %s' % e)
        return
    new_content = _rewrite_spamd_config(facts, content)
    if new_content == content:
        api.current_logger().info('There is nothing to migrate in the spamd configuration file')
        return
    try:
        backup_path = backup_func(utils.SYSCONFIG_SPAMASSASSIN)
        api.current_logger().info('spamd configuration file backup created at %s.'
                                  % backup_path)
    except (OSError, IOError) as e:
        api.current_logger().warning(
            'spamd configuration file migration will not be performed. Failed to create backup: %s' % e)
        return
    try:
        fileops.write(utils.SYSCONFIG_SPAMASSASSIN, new_content)
    except (OSError, IOError) as e:
        api.current_logger().warning('Failed to rewrite the spamd configuration file: %s' % e)
