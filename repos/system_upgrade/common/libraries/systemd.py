import fnmatch
import os

from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import SystemdServiceFile, SystemdServicePreset

SYSTEMD_SYMLINKS_DIR = '/etc/systemd/system/'

_SYSTEMCTL_CMD_OPTIONS = ['--type=service', '--all', '--plain', '--no-legend']
_USR_PRESETS_PATH = '/usr/lib/systemd/system-preset/'
_ETC_PRESETS_PATH = '/etc/systemd/system-preset/'

SYSTEMD_SYSTEM_LOAD_PATH = [
    '/etc/systemd/system',
    '/usr/lib/systemd/system'
]


def get_broken_symlinks():
    """
    Get broken systemd symlinks on the system

    :return: List of broken systemd symlinks
    :rtype: list[str]
    :raises: CalledProcessError: if the `find` command fails
    :raises: OSError: if the find utility is not found
    """
    try:
        return run(['find', SYSTEMD_SYMLINKS_DIR, '-xtype', 'l'], split=True)['stdout']
    except (OSError, CalledProcessError):
        api.current_logger().error('Cannot obtain the list of broken systemd symlinks.')
        raise


def _try_call_unit_command(command, unit):
    try:
        # it is possible to call this on multiple units at once,
        # but failing to enable one service would cause others to not enable as well
        run(['systemctl', command, unit])
    except CalledProcessError as err:
        msg = 'Failed to {} systemd unit "{}". Message: {}'.format(command, unit, str(err))
        api.current_logger().error(msg)
        raise err


def enable_unit(unit):
    """
    Enable a systemd unit

    It is strongly recommended to produce SystemdServicesTasks message instead,
    unless it is absolutely necessary to handle failure yourself.

    :param unit: The systemd unit to enable
    :raises CalledProcessError: In case of failure
    """
    _try_call_unit_command('enable', unit)


def disable_unit(unit):
    """
    Disable a systemd unit

    It is strongly recommended to produce SystemdServicesTasks message instead,
    unless it is absolutely necessary to handle failure yourself.

    :param unit: The systemd unit to disable
    :raises CalledProcessError: In case of failure
    """
    _try_call_unit_command('disable', unit)


def reenable_unit(unit):
    """
    Re-enable a systemd unit

    It is strongly recommended to produce SystemdServicesTasks message, unless it
    is absolutely necessary to handle failure yourself.

    :param unit: The systemd unit to re-enable
    :raises CalledProcessError: In case of failure
    """
    _try_call_unit_command('reenable', unit)


def get_service_files():
    """
    Get list of unit files of systemd services on the system

    The list includes template units.

    :return: List of service unit files with states
    :rtype: list[SystemdServiceFile]
    :raises: CalledProcessError: in case of failure of `systemctl` command
    """
    services_files = []
    try:
        cmd = ['systemctl', 'list-unit-files'] + _SYSTEMCTL_CMD_OPTIONS
        service_units_data = run(cmd, split=True)['stdout']
    except CalledProcessError as err:
        api.current_logger().error('Cannot obtain the list of unit files:{}'.format(str(err)))
        raise

    for entry in service_units_data:
        columns = entry.split()
        services_files.append(SystemdServiceFile(name=columns[0], state=columns[1]))
    return services_files


def _join_presets_resolving_overrides(etc_files, usr_files):
    """
    Join presets and resolve preset file overrides

    Preset files in /etc/ override those with the same name in /usr/.
    If such a file is a symlink to /dev/null, it disables the one in /usr/ instead.

    :param etc_files: Systemd preset files in /etc/
    :param usr_files: Systemd preset files in /usr/
    :return: List of preset files in /etc/ and /usr/ with overridden files removed
    """
    for etc_file in etc_files:
        filename = os.path.basename(etc_file)
        for usr_file in usr_files:
            if filename == os.path.basename(usr_file):
                usr_files.remove(usr_file)
                if os.path.islink(etc_file) and os.readlink(etc_file) == '/dev/null':
                    etc_files.remove(etc_file)

    return etc_files + usr_files


def _search_preset_files(path):
    """
    Search preset files in the given path

    Presets are search recursively in the given directory.
    If path isn't an existing directory, return empty list.

    :param path: The path to search preset files in
    :return: List of found preset files
    :rtype: list[str]
    :raises: CalledProcessError: if the `find` command fails
    :raises: OSError: if the find utility is not found
    """
    if os.path.isdir(path):
        try:
            return run(['find', path, '-name', '*.preset'], split=True)['stdout']
        except (OSError, CalledProcessError) as err:
            api.current_logger().error('Cannot obtain list of systemd preset files in {}:{}'.format(path, str(err)))
            raise
    else:
        return []


def _get_system_preset_files():
    """
    Get systemd system preset files and remove overriding entries. Entries in /run/systemd/system are ignored.

    :return: List of system systemd preset files
    :raises: CalledProcessError: if the `find` command fails
    :raises: OSError: if the find utility is not found
    """
    etc_files = _search_preset_files(_ETC_PRESETS_PATH)
    usr_files = _search_preset_files(_USR_PRESETS_PATH)

    preset_files = _join_presets_resolving_overrides(etc_files, usr_files)
    preset_files.sort()
    return preset_files


def _recursive_glob(pattern, root_dir):
    for _, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if fnmatch.fnmatch(filename, pattern):
                yield filename


def _parse_preset_entry(entry, presets, load_path):
    """
    Parse a single entry (line) in a preset file

    Single entry might set presets on multiple units using globs.

    :param entry: The entry to parse
    :param presets: Dictionary to store the presets into
    :param load_path: List of paths to look systemd unit files up in
    """

    columns = entry.split()
    if len(columns) < 2 or columns[0] not in ('enable', 'disable'):
        raise ValueError('Invalid preset file entry: "{}"'.format(entry))

    for path in load_path:
        # TODO(mmatuska): This currently also globs non unit files,
        # so the results need to be filtered with something like endswith('.<unit_type>')
        unit_files = _recursive_glob(columns[1], root_dir=path)

        for unit_file in unit_files:
            if '@' in columns[1] and len(columns) > 2:
                # unit is a template,
                # if the entry contains instance names after template unit name
                # the entry only applies to the specified instances, not to the
                # template itself
                for instance in columns[2:]:
                    service_name = unit_file[:unit_file.index('@') + 1] + instance + '.service'
                    if service_name not in presets:  # first occurrence has priority
                        presets[service_name] = columns[0]

            elif unit_file not in presets:  # first occurrence has priority
                presets[unit_file] = columns[0]


def _parse_preset_files(preset_files, load_path, ignore_invalid_entries):
    """
    Parse presets from preset files

    :param load_path: List of paths to search units at
    :param ignore_invalid_entries: Whether to ignore invalid entries in preset files or raise an error
    :return: Dictionary mapping systemd units to their preset state
    :rtype: dict[str, str]
    :raises: ValueError: when a preset file has invalid content
    """
    presets = {}

    for preset in preset_files:
        with open(preset, 'r') as preset_file:
            for line in preset_file:
                stripped = line.strip()
                if stripped and stripped[0] not in ('#', ';'):  # ignore comments
                    try:
                        _parse_preset_entry(stripped, presets, load_path)
                    except ValueError as err:
                        new_msg = 'Invalid preset file {pfile}: {error}'.format(pfile=preset, error=str(err))
                        if ignore_invalid_entries:
                            api.current_logger().warning(new_msg)
                            continue
                        raise ValueError(new_msg)
    return presets


def get_system_service_preset_files(service_files, ignore_invalid_entries=False):
    """
    Get system preset files for services

    Presets for static and transient services are filtered out.

    :param services_files: List of service unit files
    :param ignore_invalid_entries: Ignore invalid entries in preset files if True, raise ValueError otherwise
    :return: List of system systemd services presets
    :rtype: list[SystemdServicePreset]
    :raises: CalledProcessError: In case of errors when discovering systemd preset files
    :raises: OSError: When the `find` command is not available
    :raises: ValueError: When a preset file has invalid content and ignore_invalid_entries is False
    """
    preset_files = _get_system_preset_files()
    presets = _parse_preset_files(preset_files, SYSTEMD_SYSTEM_LOAD_PATH, ignore_invalid_entries)

    preset_models = []
    for unit, state in presets.items():
        if unit.endswith('.service'):
            service_file = next(iter([s for s in service_files if s.name == unit]), None)
            # presets can also be set on instances of template services which don't have a unit file
            if service_file and service_file.state in ('static', 'transient'):
                continue
            preset_models.append(SystemdServicePreset(service=unit, state=state))

    return preset_models
