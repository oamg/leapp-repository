import os
import re

from leapp.libraries.actor import pluginscanner
from leapp.libraries.stdlib import api
from leapp.models import PkgManagerInfo

YUM_CONFIG_PATH = '/etc/yum.conf'
DNF_CONFIG_PATH = '/etc/dnf/dnf.conf'

RELEASEVER_PATH = '/etc/dnf/vars/releasever'


def _releasever_exists(releasever_path):
    return os.path.isfile(releasever_path)


def get_etc_releasever():
    """ Get release version from "/etc/dnf/vars/releasever" file """

    if not _releasever_exists(RELEASEVER_PATH):
        return None

    with open(RELEASEVER_PATH, 'r') as fo:
        # we care about the first line only
        releasever = fo.readline().strip()

    return releasever


def _get_config_contents(config_path):
    if os.path.isfile(config_path):
        with open(config_path, 'r') as config:
            return config.read()
    return ''


def _get_proxy_if_set(manager_config_path):
    """
    Get proxy address from specified package manager config.

    :param str manager_config_path: path to a package manager config
    :returns: proxy address or None when not set
    :rtype: str
    """

    config = _get_config_contents(manager_config_path)

    for line in config.split('\n'):
        if re.match('^proxy[ \t]*=', line):
            proxy_address = line.split('=', 1)[1]
            return proxy_address.strip()

    return None


def get_configured_proxies():
    """
    Get a list of proxies used in dnf and yum configuration files.

    :returns: sorted list of unique proxies
    :rtype: List
    """

    configured_proxies = set()
    for config_path in (DNF_CONFIG_PATH, YUM_CONFIG_PATH):
        proxy = _get_proxy_if_set(config_path)
        if proxy:
            configured_proxies.add(proxy)

    return sorted(configured_proxies)


def process():
    pkg_manager_info = PkgManagerInfo()
    pkg_manager_info.etc_releasever = get_etc_releasever()
    pkg_manager_info.configured_proxies = get_configured_proxies()
    pkg_manager_info.enabled_plugins = pluginscanner.scan_enabled_package_manager_plugins()

    api.produce(pkg_manager_info)
