import re

from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.stdlib import run

# When the output spans multiple lines, each of the lines after the first one
# start with a '    <SPACES>    : '
LOADED_PLUGINS_NEXT_LINE_START = ' +: '


def _parse_loaded_plugins(package_manager_output):
    """
    Retrieves a list of plugins that are being loaded when calling dnf/yum.

    :param dict package_manager_output: The result of running the package manager command.
    :rtype: list
    :returns: A list of plugins that are being loaded by the package manager.
    """
    # Package manager might break the information about loaded plugins into multiple lines,
    # we need to concaternate the list ourselves
    loaded_plugins_str = ''
    for line in package_manager_output['stdout']:
        if line.startswith('Loaded plugins:'):
            # We have found the first line that contains the plugins
            plugins_on_this_line = line[16:]  # Remove the `Loaded plugins: ` part

            if plugins_on_this_line[-1] == ',':
                plugins_on_this_line += ' '

            loaded_plugins_str += plugins_on_this_line
            continue

        if loaded_plugins_str:
            if re.match(LOADED_PLUGINS_NEXT_LINE_START, line):
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


def scan_enabled_package_manager_plugins():
    """
    Runs package manager (yum/dnf) command and parses its output for enabled/loaded plugins.

    :return: A list of enabled plugins.
    :rtype: List
    """

    # We rely on package manager itself to report what plugins are used when it is invoked.
    # An alternative approach would be to check the install path for package manager plugins
    # and parse corresponding plugin configuration files.

    if get_source_major_version() == '7':
        # in case of yum, set debuglevel=2 to be sure the output is always
        # same. The format of data is different for various debuglevels
        cmd = ['yum', '--setopt=debuglevel=2']
    else:
        # the verbose mode in dnf always set particular debuglevel, so the
        # output is not affected by the default debug level set on the
        # system
        cmd = ['dnf', '-v']  # On RHEL8 we need to supply an extra switch

    pkg_manager_output = run(cmd, split=True, checked=False)  # The command will certainly fail (does not matter).

    return _parse_loaded_plugins(pkg_manager_output)
