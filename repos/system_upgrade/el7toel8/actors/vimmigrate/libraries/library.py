from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM


def _append_string(path, content):
    """
    Appends string into file

    :param str path: path to file
    :param str content: content to add
    """
    with open(path, 'a') as f:
        f.write(content)


# rpm : the default config file
vim_configs = {
    'vim-minimal': '/etc/virc',
    'vim-enhanced': '/etc/vimrc'
}


# list of macros that should be set
new_macros = [
    'let skip_defaults_vim=1',
    'set t_BE='
]


def update_config(path, append_function=_append_string):
    """
    Insert expected content into the file on the path

    :param str path: string representing the full path of the config file
    :param func append_function: appends string into file
    """
    fmt_input = "\n{comment_line}\n{content}\n".format(comment_line='" content added by Leapp',
                                                       content='\n'.join(new_macros))

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


def update_vim(debug_log=api.current_logger().debug,
               error_log=api.current_logger().error,
               is_installed=_check_package,
               append_function=_append_string):
    """
    Do update of configuration files

    :param func debug_log: function for debug logging
    :param func error_log: function for error logging
    :param func is_installed: checks if a package is installed
    :param func append_function: appends string into file
    """
    error_list = []

    for pkg, config_file in vim_configs.items():
        if not is_installed(pkg):
            continue

        debug_log('Updating Vim configuration file {}.'.format(config_file))

        try:
            update_config(config_file, append_function)
        except (OSError, IOError) as error:
            error_list.append((config_file, error))
    if error_list:
        error_log('The files below have not been modified (error message included):' +
                  ''.join(['\n    - {}: {}'.format(err[0], err[1]) for err in error_list]))
