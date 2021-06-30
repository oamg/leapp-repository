import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import run, CalledProcessError
from leapp.models import EnvVar, OSRelease


ENV_IGNORE = ('LEAPP_CURRENT_PHASE', 'LEAPP_CURRENT_ACTOR', 'LEAPP_VERBOSE',
              'LEAPP_DEBUG')

ENV_MAPPING = {'LEAPP_DEVEL_DM_DISABLE_UDEV': 'DM_DISABLE_UDEV'}


LEAPP_UPGRADE_FLAVOUR_DEFAULT = 'default'
LEAPP_UPGRADE_FLAVOUR_SAP_HANA = 'saphana'

HANA_BASE_PATH = '/hana/shared'
HANA_SAPCONTROL_PATH = 'exe/linuxx86_64/hdb/sapcontrol'

# map of expected upgrade paths per source system and flavour, expected
# does not mean supported. Supported paths are checked later.
upgrade_paths_map = {

    # expected upgrade paths for RHEL 7
    ('7.6', LEAPP_UPGRADE_FLAVOUR_DEFAULT): '8.4',
    ('7.9', LEAPP_UPGRADE_FLAVOUR_DEFAULT): '8.4',
    ('7.7', LEAPP_UPGRADE_FLAVOUR_SAP_HANA): '8.2',

    # expected upgrade paths for RHEL 8
    ('8.6', LEAPP_UPGRADE_FLAVOUR_DEFAULT): '9.0',

    # unsupported fallback paths for RHEL 7
    ('7', LEAPP_UPGRADE_FLAVOUR_DEFAULT): '8.4',
    ('7', LEAPP_UPGRADE_FLAVOUR_SAP_HANA): '8.4',

    # unsupported fallback paths for RHEL 8
    ('8', LEAPP_UPGRADE_FLAVOUR_DEFAULT): '9.0',
}


def _get_major_version(version):
    return version.split('.')[0]


def get_env_vars():
    """
    Gather LEAPP_DEVEL environment variables and respective mappings to provide them as messages to be
    available after reboot.
    """
    env_vars = []
    leapp_vars = {k: v for (k, v) in os.environ.items() if k.startswith('LEAPP_') and k not in ENV_IGNORE}
    for k, v in leapp_vars.items():
        if k in ENV_MAPPING:
            env_vars.append(EnvVar(name=ENV_MAPPING.get(k), value=v))
            continue
        env_vars.append(EnvVar(name=k, value=v))

    return env_vars


def get_os_release(path):
    """Retrieve data about System OS release from provided file."""
    try:
        with open(path) as f:
            data = dict(l.strip().split('=', 1) for l in f.readlines() if '=' in l)
            return OSRelease(
                release_id=data.get('ID', '').strip('"'),
                name=data.get('NAME', '').strip('"'),
                pretty_name=data.get('PRETTY_NAME', '').strip('"'),
                version=data.get('VERSION', '').strip('"'),
                version_id=data.get('VERSION_ID', '').strip('"'),
                variant=data.get('VARIANT', '').strip('"') or None,
                variant_id=data.get('VARIANT_ID', '').strip('"') or None
            )
    except IOError as e:
        raise StopActorExecutionError(
            message='Cannot collect the system OS facts.',
            details={'details': str(e)}
        )


def get_booted_kernel():
    """
    Get version and release of the currently used kernel in one string.
    """
    try:
        return run(['/usr/bin/uname', '-r'])['stdout'].strip()
    except CalledProcessError as e:
        raise StopActorExecutionError(
            message='Unable to obtain release of the booted kernel.',
            details={'details': str(e), 'stderr': e.stderr}
        )


def get_target_version(flavour=LEAPP_UPGRADE_FLAVOUR_DEFAULT):
    """
    Return the target version for the given `flavour` of upgrade. The default value for `flavour` is `default`.

    In case the environment variable `LEAPP_DEVEL_TARGET_RELEASE` is set, the value of it will be returned.
    """

    current_version_id = get_os_release('/etc/os-release').version_id
    target_version = upgrade_paths_map.get((current_version_id, flavour), None)
    if not target_version:
        # If we cannot find a particular major.minor version in the map,
        # we fallback to pick a target version just based on a major version.
        # This can happen for example when testing not yet released versions
        major_version = _get_major_version(current_version_id)
        target_version = upgrade_paths_map.get((major_version, flavour), None)

    return os.getenv('LEAPP_DEVEL_TARGET_RELEASE', None) or target_version


def detect_sap_hana():
    """
    Detect SAP HANA based on existance of /hana/shared/*/exe/linuxx86_64/hdb/sapcontrol
    """
    if os.path.exists(HANA_BASE_PATH):
        for entry in os.listdir(HANA_BASE_PATH):
            # Does /hana/shared/{entry}/exe/linuxx86_64/hdb/sapcontrol exist?
            if os.path.exists(os.path.join(HANA_BASE_PATH, entry, HANA_SAPCONTROL_PATH)):
                return True
    return False


def get_upgrade_flavour():
    """
    Returns the flavour of the upgrade for this system.
    """
    if detect_sap_hana():
        return LEAPP_UPGRADE_FLAVOUR_SAP_HANA
    return LEAPP_UPGRADE_FLAVOUR_DEFAULT
