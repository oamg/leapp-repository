import os
import pwd

from leapp.libraries.common.rpms import check_file_modification
from leapp.models import PulseAudioConfiguration

# System-wide PulseAudio configuration directory
PULSEAUDIO_CONFIG_DIR = '/etc/pulse'

# Drop-in directories included from default.pa and system.pa
_DROPIN_DIRS = (
    '/etc/pulse/default.pa.d',
    '/etc/pulse/system.pa.d',
)

# Files that are part of the default PulseAudio installation
_DEFAULT_CONFIG_FILES = frozenset((
    'client.conf',
    'daemon.conf',
    'default.pa',
    'system.pa',
))

# Per-user PulseAudio config directory relative to home
_USER_CONFIG_SUBDIR = '.config/pulse'


def _get_dropin_dirs_with_content():
    """
    Return list of drop-in directories that exist and contain files.

    PulseAudio includes fragments from /etc/pulse/default.pa.d/ and
    /etc/pulse/system.pa.d/ via .include directives. These directories
    do not exist by default.

    :return: list of drop-in directory paths that contain files
    :rtype: list
    """
    found = []
    for dropin_dir in _DROPIN_DIRS:
        if os.path.isdir(dropin_dir) and os.listdir(dropin_dir):
            found.append(dropin_dir)
    return found


def _get_user_config_dirs():
    """
    Return list of user home directories that contain PulseAudio configuration.

    Checks ~/.config/pulse/ for each user with a valid home directory.

    :return: list of per-user PulseAudio config directory paths
    :rtype: list
    """
    found = []
    for user in pwd.getpwall():
        pulse_dir = os.path.join(user.pw_dir, _USER_CONFIG_SUBDIR)
        if os.path.isdir(pulse_dir) and os.listdir(pulse_dir):
            found.append(pulse_dir)
    return sorted(found)


def _check_default_configs_modified():
    """
    Check whether any of the default PulseAudio config files have been modified.

    Uses RPM verification to detect changes to files owned by the pulseaudio
    package. Returns list of modified default config file paths.

    :return: list of modified default config file paths
    :rtype: list
    """
    modified = []
    for filename in sorted(_DEFAULT_CONFIG_FILES):
        filepath = os.path.join(PULSEAUDIO_CONFIG_DIR, filename)
        if os.path.isfile(filepath):
            if check_file_modification(filepath):
                modified.append(filepath)

    return modified


def scan_pulseaudio():
    """
    Scan the system for PulseAudio configuration and return findings.

    :return: PulseAudioConfiguration message with scan results
    :rtype: PulseAudioConfiguration
    """
    modified_defaults = _check_default_configs_modified()
    dropin_dirs = _get_dropin_dirs_with_content()
    user_config_dirs = _get_user_config_dirs()

    return PulseAudioConfiguration(
        modified_defaults=modified_defaults,
        dropin_dirs=dropin_dirs,
        user_config_dirs=user_config_dirs,
    )
