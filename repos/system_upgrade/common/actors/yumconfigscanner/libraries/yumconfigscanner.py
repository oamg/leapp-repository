import re

from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.stdlib import api, run
from leapp.models import YumConfig

# When the output spans multiple lines, each of the lines after the first one
# start with a '    <SPACES>    : '
YUM_LOADED_PLUGINS_NEXT_LINE_START = ' +: '


def _parse_loaded_plugins(yum_output):
    """
    Retrieves a list of plugins that are being loaded when calling yum.

    :param dict yum_output: The result of running the yum command.
    :rtype: list
    :returns: A list of plugins that are being loaded when calling yum.
    """
    # YUM might break the information about loaded plugins into multiple lines,
    # we need to concaternate the list ourselves
    loaded_plugins_str = ''
    for line in yum_output['stdout']:
        if line.startswith('Loaded plugins:'):
            # We have found the first line that contains the plugins
            plugins_on_this_line = line[16:]  # Remove the `Loaded plugins: ` part

            if plugins_on_this_line[-1] == ',':
                plugins_on_this_line += ' '

            loaded_plugins_str += plugins_on_this_line
            continue

        if loaded_plugins_str:
            if re.match(YUM_LOADED_PLUGINS_NEXT_LINE_START, line):
                # The list of plugins continues on this line
                plugins_on_this_line = line.lstrip(' :')  # Remove the leading spaces and semicolon

                # Plugins are separated by ', ', however the space at the end of line might get dropped, add it
                # so we can split it by ', ' later
                if plugins_on_this_line[-1] == ',':
                    plugins_on_this_line += ' '

                loaded_plugins_str += plugins_on_this_line
            else:
                # The list of loaded plugins ended
                break

    return loaded_plugins_str.split(', ')


def scan_enabled_yum_plugins():
    """
    Runs the `yum` command and parses its output for enabled/loaded plugins.

    :return: A list of enabled plugins.
    :rtype: List
    """

    # We rely on yum itself to report what plugins are used when it is invoked.
    # An alternative approach would be to check /usr/lib/yum-plugins/ (install
    # path for yum plugins) and parse corresponding configurations from
    # /etc/yum/pluginconf.d/

    if get_source_major_version() == '7':
        # in case of yum, set debuglevel=2 to be sure the output is always
        # same. The format of data is different for various debuglevels
        yum_cmd = ['yum', '--setopt=debuglevel=2']
    else:
        # the verbose mode in dnf always set particular debuglevel, so the
        # output is not affected by the default debug level set on the
        # system
        yum_cmd = ['dnf', '-v']  # On RHEL8 we need to supply an extra switch

    yum_output = run(yum_cmd, split=True, checked=False)  # The yum command will certainly fail (does not matter).

    return _parse_loaded_plugins(yum_output)


def scan_yum_config():
    """
    Scans the YUM configuration and produces :class:`YumConfig` message with the information found.
    """
    config = YumConfig()
    config.enabled_plugins = scan_enabled_yum_plugins()

    api.produce(config)
