import glob
import os

from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import DynamicLinkerConfiguration, InstalledRedHatSignedRPM, LDConfigFile, MainLDConfigFile

LD_SO_CONF_DIR = '/etc/ld.so.conf.d'
LD_SO_CONF_MAIN = '/etc/ld.so.conf'
LD_SO_CONF_DEFAULT_INCLUDE = 'ld.so.conf.d/*.conf'
LD_SO_CONF_COMMENT_PREFIX = '#'
LD_LIBRARY_PATH_VAR = 'LD_LIBRARY_PATH'
LD_PRELOAD_VAR = 'LD_PRELOAD'


def _read_file(file_path):
    with open(file_path, 'r') as fd:
        return fd.readlines()


def _is_modified(config_path):
    """ Decide if the configuration file was modified based on the package it belongs to. """
    result = run(['rpm', '-Vf', config_path], checked=False)
    if not result['exit_code']:
        return False
    modification_flags = result['stdout'].split(' ', 1)[0]
    # The file is considered modified only when the checksum does not match
    return '5' in modification_flags


def _is_included_config_custom(config_path):
    if not os.path.isfile(config_path):
        return False

    # Check if the config file has any lines that have an effect on dynamic linker configuration
    has_effective_line = False
    for line in _read_file(config_path):
        line = line.strip()
        if line and not line.startswith(LD_SO_CONF_COMMENT_PREFIX):
            has_effective_line = True
            break

    if not has_effective_line:
        return False

    is_custom = False
    try:
        package_name = run(['rpm', '-qf', '--queryformat', '%{NAME}', config_path])['stdout']
        is_custom = not has_package(InstalledRedHatSignedRPM, package_name) or _is_modified(config_path)
    except CalledProcessError:
        is_custom = True

    return is_custom


def _parse_main_config():
    """
    Extracts included configs from the main dynamic linker configuration file (/etc/ld.so.conf)
    along with lines that are likely custom. The lines considered custom are simply those that are
    not includes.

    :returns: tuple containing all the included files and lines considered custom
    :rtype:  tuple(list, list)
    """
    config = _read_file(LD_SO_CONF_MAIN)

    included_configs = []
    other_lines = []
    for line in config:
        line = line.strip()
        if line.startswith('include'):
            cfg_glob = line.split(' ', 1)[1].strip()
            cfg_glob = os.path.join('/etc', cfg_glob) if not os.path.isabs(cfg_glob) else cfg_glob
            included_configs.append(cfg_glob)
        elif line and not line.startswith(LD_SO_CONF_COMMENT_PREFIX):
            other_lines.append(line)

    return included_configs, other_lines


def scan_dynamic_linker_configuration():
    included_configs, other_lines = _parse_main_config()

    is_default_include_present = '/etc/' + LD_SO_CONF_DEFAULT_INCLUDE in included_configs
    if not is_default_include_present:
        api.current_logger().debug('The default include "{}" is not present in '
                                   'the {} file.'.format(LD_SO_CONF_DEFAULT_INCLUDE, LD_SO_CONF_MAIN))

    if is_default_include_present and len(included_configs) != 1:
        # The additional included configs will most likely be created manually by the user
        # and therefore will get flagged as custom in the next part of this function
        api.current_logger().debug('The default include "{}" is not the only include in '
                                   'the {} file.'.format(LD_SO_CONF_DEFAULT_INCLUDE, LD_SO_CONF_MAIN))

    main_config_file = MainLDConfigFile(path=LD_SO_CONF_MAIN, modified=any(other_lines), modified_lines=other_lines)

    # Expand the config paths from globs and ensure uniqueness of resulting paths
    config_paths = set()
    for cfg_glob in included_configs:
        for cfg in glob.glob(cfg_glob):
            config_paths.add(cfg)

    included_config_files = []
    for config_path in config_paths:
        config_file = LDConfigFile(path=config_path, modified=_is_included_config_custom(config_path))
        included_config_files.append(config_file)

    # Check if dynamic linker variables used for specifying custom libraries are set
    variables = [LD_LIBRARY_PATH_VAR, LD_PRELOAD_VAR]
    used_variables = [var for var in variables if os.getenv(var, None)]

    configuration = DynamicLinkerConfiguration(main_config=main_config_file,
                                               included_configs=included_config_files,
                                               used_variables=used_variables)

    if other_lines or any([config.modified for config in included_config_files]) or used_variables:
        api.produce(configuration)
