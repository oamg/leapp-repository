import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import CupsChangedFeatures, InstalledRedHatSignedRPM


def _list_dir(path):
    """
    Lists files which are in a directory specified by the path.

    :param str path: path to directory
    """
    return os.listdir(path)


def _path_exists(path):
    """
    Checks if the path exists on the machine.

    :param str path: path to file/directory
    """
    return os.path.exists(path)


def _read_file(path):
    """
    Read a file line by line.

    :param str path: path to file
    """
    with open(path, 'r') as f:
        return f.readlines()


def _check_package(pkg):
    """
    Checks if a package is installed and signed.

    :param str pkg: name of package
    """
    return has_package(InstalledRedHatSignedRPM, pkg)


def directive_exists(name, line):
    """
    Checks if directive exists in the line, but it is not
    commented out.

    :param str name: name of directive
    :param str line: line of file
    """
    return line.lstrip().startswith(name)


def get_directive_value(name, line):
    """
    Returns directive value.

    :param str name: name of directive
    :param str line: line of file
    """
    if directive_exists(name, line):
        return line.lstrip().lstrip(name).lstrip().split(' ')[0].rstrip()
    return None


def interface_script_check(check_path_func=_path_exists,
                           list_dir_func=_list_dir):
    """
    Checks if any file is in /etc/cups/interfaces, which means there could be
    print queues using interface script.

    :param func check_path_func: checks if /etc/cups/interfaces exists
    :param func list_dir_func: lists contents of directory
    """
    if (
            check_path_func('/etc/cups/interfaces') and
            list_dir_func('/etc/cups/interfaces')
       ):
        return True
    return False


def include_directive_check(read_func=_read_file):
    """
    Checks if 'Include' directive is present.

    :param str paths: path to cupsd configuration file
    :param func read_func: function for reading a file as lines
    """
    included_files = ['/etc/cups/cupsd.conf']
    error_list = []

    vetted_included_files = []
    while included_files:
        # NOTE(ivasilev) Will be using stack to process last encountered include directives first
        included_file = included_files.pop(-1)
        try:
            lines = read_func(included_file)
        except IOError:
            error_list.append('Error during reading file {}: file not'
                              ' found'.format(included_file))
            continue
        # Append to the resulting list of vetted files if exception wasn't raised
        vetted_included_files.append(included_file)
        # Mark any other included file you find as need-to-be-validated
        includes_to_process = []
        for line in lines:
            value = get_directive_value('Include', line)
            if value:
                includes_to_process.append(value)
        # NOTE(ivasilev) Add discovered Include directives to the stack in reversed order, so that they are processed
        # in the same order they appeared in the file
        included_files.extend(reversed(includes_to_process))

    return (vetted_included_files, error_list)


def digest_directive_check(path, read_func=_read_file):
    """
    Checks if AuthType or DefaultAuthType directives contain
    Digest or BasicDigest values, which were removed.

    :param str path: path to configuration file
    :param func read_func: function for reading the file
    """
    lines = read_func(path)

    for line in lines:
        for name in ['AuthType', 'DefaultAuthType']:
            for value in ['Digest', 'BasicDigest']:
                found_value = get_directive_value(name, line)
                if found_value == value:
                    return True
    return False


def ssl_directive_check(read_func=_read_file):
    """
    Checks if ServerCertificate or ServerKey directives are
    used in cups-files.conf.

    :param func read_func: function for reading the file
    """
    lines = read_func('/etc/cups/cups-files.conf')

    for line in lines:
        for name in ['ServerCertificate', 'ServerKey']:
            value = get_directive_value(name, line)
            if value:
                return True
    return False


def environment_setup_check(path, read_func=_read_file):
    """
    Checks if PassEnv or SetEnv directives are used in configuration.
    They were moved to cups-files.conf in newer CUPS due security
    issues.

    :param str path: path to configuration file
    :param func read_func: reads the file
    """
    lines = read_func(path)

    for line in lines:
        for name in ['SetEnv', 'PassEnv']:
            value = get_directive_value(name, line)
            if value:
                return True
    return False


def print_capabilities_check(path, read_func=_read_file):
    """
    Checks if PrintcapFormat directive is used in configuration.
    It was moved to cups-files.conf in newer CUPS.

    :param str path: path to configuration file
    :param func read_func: reads the file
    """
    lines = read_func(path)

    for line in lines:
        value = get_directive_value('PrintcapFormat', line)
        if value:
            return True
    return False


def _send_model(interface, digest, include, certkey, env,
                printcap, include_files_list):
    """
    Produces model of facts.

    :param bool interface: true if interface scripts are used
    :param bool digest: true if BasicDigest/Digest values are used
    :param bool include: true if Include directive is used
    :param bool certkey: true if ServerCertificate/ServerKey directives are used
    :param bool env: true if PassEnv/SetEnv directives are used
    :param bool printcap: true if PrintcapFormat directive is used
    :param list include_files_list: contains paths to included files
    """
    api.produce(CupsChangedFeatures(interface=interface,
                                    digest=digest,
                                    include=include,
                                    certkey=certkey,
                                    env=env,
                                    printcap=printcap,
                                    include_files=include_files_list))


def find_features(debug_log=api.current_logger().debug,
                  warn_log=api.current_logger().warn,
                  error_log=api.current_logger().error,
                  send_features=_send_model,
                  is_installed=_check_package,
                  read_func=_read_file,
                  check_path_func=_path_exists,
                  list_dir_func=_list_dir):
    """
    Checks every feature which changed between CUPS 1.6.3 and CUPS
    2.2.6.

    :param func debug_log: function for debug logging
    :param func error_log: function for error logging
    :param func warn_log: function for warning logging
    :param func send_features: produces CupsMigrationModel if necessary
    :param func is_installed: check if the package is installed
    :param func read_func: reads a file
    :param func check_path_func: checks if the file exists
    :param func list_dir_func: list files in a directory
    """

    if not is_installed('cups'):
        return

    if (
        not check_path_func('/etc/cups/cupsd.conf') or
        not check_path_func('/etc/cups/cups-files.conf')
    ):
        # seatbelt - it's expected as super rare to have malfunction cupsd :)
        raise StopActorExecutionError('Core CUPS configuration files '
                                      'are missing. CUPS installation '
                                      'is corrupted, terminating the actor.')

    debug_log('Checking if CUPS configuration contains removed features.')

    digest = env = printcap = interface = certkey = include = False

    include_file_list, error_list = include_directive_check(read_func)

    if error_list:
        warn_log('Following included files will not be appended to '
                 'cupsd.conf due attached error:'
                 + ''.join(['\n   - {}'.format(err) for err in error_list]))

    if len(include_file_list) > 1:
        include = True

    interface = interface_script_check(check_path_func, list_dir_func)

    for config_file in include_file_list:

        if not digest:
            digest = digest_directive_check(config_file, read_func)

        if not env:
            env = environment_setup_check(config_file, read_func)

        if not printcap:
            printcap = print_capabilities_check(config_file, read_func)

    certkey = ssl_directive_check(read_func)

    if any([interface, digest, include, certkey, env, printcap]):
        send_features(interface, digest, include, certkey, env,
                      printcap, include_file_list)
