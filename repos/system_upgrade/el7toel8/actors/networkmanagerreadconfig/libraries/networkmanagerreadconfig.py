from six.moves.configparser import ParsingError

from leapp.libraries.common import utils
from leapp.libraries.stdlib import api, CalledProcessError, run


def read_nm_config(file_path=None):
    if file_path:
        try:
            with open(file_path, 'r') as f:
                r = f.read()
                return r
        except IOError as e:
            api.current_logger().warning('Error reading NetworkManager configuration from {}: {}'.format(file_path, e))
            return None
    else:
        try:
            # Use 'NM --print-config' to read the configurationo so
            # that the main configuration file and other files in
            # various directories get merged in the right way.
            r = run(['NetworkManager', '--print-config'], split=False)['stdout']
            return r
        except (OSError, CalledProcessError) as e:
            api.current_logger().warning('Error reading NetworkManager configuration: {}'.format(e))
            return None


def parse_nm_config(cfg):
    try:
        return utils.parse_config(cfg)
    except (ParsingError, TypeError) as e:
        api.current_logger().warning('Error parsing NetworkManager configuration: {}'.format(e))
        return None


def check_nm_dhcp(nm_cfg, parser):
    if parser.has_option('main', 'dhcp'):
        nm_cfg.dhcp = parser.get("main", "dhcp")
