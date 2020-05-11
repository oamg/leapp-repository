import errno
import os

from leapp.libraries.actor import config_parser
from leapp.libraries.common import vsftpdutils as utils
from leapp.libraries.stdlib import api
from leapp.models import VsftpdConfig, VsftpdFacts


def _parse_config(path, content):
    try:
        parser = config_parser.VsftpdConfigParser(content)
        return parser.parsed_config
    except config_parser.ParsingError:
        api.current_logger().info('File %s does not look like vsftpd configuration, skipping.'
                                  % path)
        return None


def _get_parsed_configs(read_func=utils.read_file, listdir=os.listdir):
    res = []
    try:
        for fname in listdir(utils.VSFTPD_CONFIG_DIR):
            path = os.path.join(utils.VSFTPD_CONFIG_DIR, fname)
            if not path.endswith('.conf'):
                continue
            content = utils.get_config_contents(path, read_func=read_func)
            if content is None:
                continue
            parsed = _parse_config(path, content)
            if parsed is not None:
                res.append((path, parsed))
    except OSError as e:
        if e.errno != errno.ENOENT:
            api.current_logger().warning('Failed to read vsftpd configuration directory: %s'
                                         % e)
    return res


def get_vsftpd_facts(read_func=utils.read_file, listdir=os.listdir):
    config_hash = utils.get_default_config_hash(read_func=read_func)
    configs = _get_parsed_configs(read_func=read_func, listdir=listdir)
    res_configs = []
    for path, config in configs:
        res_configs.append(VsftpdConfig(path=path,
                                        strict_ssl_read_eof=config.get(utils.STRICT_SSL_READ_EOF),
                                        tcp_wrappers=config.get(utils.TCP_WRAPPERS)))
    return VsftpdFacts(default_config_hash=config_hash, configs=res_configs)


def is_processable(installed_rpm_facts):
    for pkg in installed_rpm_facts.items:
        if pkg.name == 'vsftpd':
            return True
    return False
