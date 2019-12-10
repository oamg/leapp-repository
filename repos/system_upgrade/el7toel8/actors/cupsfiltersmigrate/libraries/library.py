from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM

# rpm : the default config file
BROWSED_CONFIG = '/etc/cups/cups-browsed.conf'


# The list of macros that should be set to get the behavior
# from previous RHEL
NEW_MACROS = [
    ('LocalQueueNamingRemoteCUPS', 'RemoteName'),
    ('CreateIPPPrinterQueues', 'All')
]


def _macro_exists(path, macro):
    """
    Check if macro is in the file.

    :param str path: string representing the full path of the config file
    :param str macro: new directive to be added
    :return boolean res: macro does/does not exist in the file
    """
    with open(path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        if line.lstrip().startswith(macro):
            return True
    return False


def _append_string(path, content):
    """
    Append string at the end of file.

    :param str path: string representing the full path of file
    :param str content: preformatted string to be added
    """
    with open(path, 'a') as f:
        f.write(content)


def update_config(path, check_function=_macro_exists,
                  append_function=_append_string):
    """
    Insert expected content into the file on the path if it is not
    in the file already.

    :param str path: string representing the full path of the config file
    :param func check_function: function to be used to check if string is in the file
    :param func append_function: function to be used to append string
    """

    macros = []
    for macro in NEW_MACROS:
        if not check_function(path, macro[0]):
            macros.append(' '.join(macro))

    if not macros:
        return

    fmt_input = "\n{comment_line}\n{content}\n".format(comment_line='# content added by Leapp',
                                                       content='\n'.join(macros))

    try:
        append_function(path, fmt_input)
    except IOError:
        raise IOError('Error during writing to file: {}.'.format(path))


def _check_package(pkg):
    """
    Checks if a package is installed and signed

    :param str pkg: name of package
    """
    return has_package(InstalledRedHatSignedRPM, pkg)


def update_cups_browsed(debug_log=api.current_logger().debug,
                        error_log=api.current_logger().error,
                        is_installed=_check_package,
                        append_function=_append_string,
                        check_function=_macro_exists):
    """
    Update cups-browsed configuration file

    :param func debug_log: function for debug logging
    :param func error_log: function for error logging
    :param func is_installed: checks if the package is installed
    :param func append_function: appends string into file
    :param func check_function: checks if macro is in the file
    """

    error_list = []

    if not is_installed('cups-filters'):
        return

    debug_log('Updating cups-browsed configuration file {}.'
              .format(BROWSED_CONFIG))

    try:
        update_config(BROWSED_CONFIG,
                      check_function,
                      append_function)
    except (OSError, IOError) as error:
        error_list.append((BROWSED_CONFIG, error))
    if error_list:
        error_log('The files below have not been modified '
                  '(error message included):' +
                  ''.join(['\n    - {}: {}'.format(err[0], err[1])
                          for err in error_list]))
        return
