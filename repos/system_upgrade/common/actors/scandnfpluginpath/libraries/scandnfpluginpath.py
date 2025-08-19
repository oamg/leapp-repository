import os

from six.moves import configparser

from leapp.libraries.stdlib import api
from leapp.models import DnfPluginPathDetected

DNF_CONFIG_PATH = '/etc/dnf/dnf.conf'


def _is_pluginpath_set(config_path):
    """Check if pluginpath option is set in DNF configuration file."""
    if not os.path.isfile(config_path):
        return False

    parser = configparser.ConfigParser()

    try:
        parser.read(config_path)
        return parser.has_option('main', 'pluginpath')
    except (configparser.Error, IOError):
        return False


def scan_dnf_pluginpath():
    """Scan DNF configuration and produce DnfPluginPathDetected message."""
    is_detected = _is_pluginpath_set(DNF_CONFIG_PATH)
    api.produce(DnfPluginPathDetected(is_pluginpath_detected=is_detected))
