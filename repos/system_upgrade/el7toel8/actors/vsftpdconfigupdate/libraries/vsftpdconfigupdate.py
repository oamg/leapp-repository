import re

from leapp.libraries.common.vsftpdutils import (
    get_default_config_hash,
    STRICT_SSL_READ_EOF,
    TCP_WRAPPERS,
    VSFTPD_DEFAULT_CONFIG_PATH
)
from leapp.libraries.stdlib import api

ANONYMOUS_ENABLE = 'anonymous_enable'


class FileOperations(object):
    def read(self, path):
        with open(path, 'r') as f:
            return f.read()

    def write(self, path, content):
        with open(path, 'w') as f:
            f.write(content)


def _replace_in_config(config_lines, option, value):
    res = []
    for line in config_lines:
        if re.match(r'^\s*' + option, line) is None:
            res.append(line)
        else:
            res.append('# Commented out by Leapp:')
            res.append('#' + line)
    if value is not None:
        res.append('# Added by Leapp:')
        res.append('%s=%s' % (option, value))
    return res


def _restore_default_config_file(fileops=FileOperations()):
    try:
        content = fileops.read(VSFTPD_DEFAULT_CONFIG_PATH)
    except IOError as e:
        api.current_logger().warning('Failed to read vsftpd configuration file: %s' % e)
        return
    lines = content.split('\n')
    lines = _replace_in_config(lines, ANONYMOUS_ENABLE, 'YES')
    content = '\n'.join(lines)
    content += '\n'
    fileops.write(VSFTPD_DEFAULT_CONFIG_PATH, content)


def _migrate_config(config, fileops=FileOperations()):
    if not config.tcp_wrappers and config.strict_ssl_read_eof is not None:
        return
    try:
        content = fileops.read(config.path)
    except IOError as e:
        api.current_logger().warning('Failed to read vsftpd configuration file %s: %s'
                                     % (config.path, e))
        return
    lines = content.split('\n')
    if config.tcp_wrappers:
        lines = _replace_in_config(lines, TCP_WRAPPERS, 'NO')
    if config.strict_ssl_read_eof is None:
        lines = _replace_in_config(lines, STRICT_SSL_READ_EOF, 'NO')
    content = '\n'.join(lines)
    content += '\n'
    try:
        fileops.write(config.path, content)
    except IOError as e:
        api.current_logger().warning('Failed to write vsftpd configuration file %s: %s'
                                     % (config.path, e))


def migrate_configs(facts, fileops=FileOperations()):
    if facts.default_config_hash is not None:
        new_hash = get_default_config_hash(read_func=fileops.read)
        # If the default config file was unmodified, it got replaced during the RPM upgrade,
        # so we have to change it back.
        if facts.default_config_hash != new_hash:
            _restore_default_config_file(fileops=fileops)
    for config in facts.configs:
        _migrate_config(config, fileops=fileops)
