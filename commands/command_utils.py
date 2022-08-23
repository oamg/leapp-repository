import json
import os
import re

from leapp.exceptions import CommandError
from leapp.utils import path

HANA_BASE_PATH = '/hana/shared'
HANA_SAPCONTROL_PATH = 'exe/linuxx86_64/hdb/sapcontrol'

LEAPP_UPGRADE_FLAVOUR_DEFAULT = 'default'
LEAPP_UPGRADE_FLAVOUR_SAP_HANA = 'saphana'
LEAPP_UPGRADE_PATHS = 'upgrade_paths.json'

VERSION_REGEX = re.compile(r"^([1-9]\d*)\.(\d+)$")


def check_version(version):
    """
    Versioning schema: MAJOR.MINOR
    In case version contains an invalid version string, an CommandError will be raised.

    :raises: CommandError
    :return: release tuple
    """
    if not re.match(VERSION_REGEX, version):
        raise CommandError('Unexpected format of target version: {}'.format(version))
    return version.split('.')[0]


def get_major_version(version):
    """
    Return the major version from the given version string.

    Versioning schema: MAJOR.MINOR.PATCH

    :param str version: The version string according to the versioning schema described.
    :rtype: str
    :returns: The major version from the given version string.
    """
    return str(check_version(version)[0])


def detect_sap_hana():
    """
    Detect SAP HANA based on existence of /hana/shared/*/exe/linuxx86_64/hdb/sapcontrol
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


def get_os_release_version_id(filepath):
    """
    Retrieve data about System OS release from provided file.

    :return: `str` version_id
    """
    with open(filepath) as f:
        data = dict(l.strip().split('=', 1) for l in f.readlines() if '=' in l)
        return data.get('VERSION_ID', '').strip('"')


def get_upgrade_paths_config():
    # NOTE(ivasilev) Importing here not to have circular dependencies
    from leapp.cli.commands.upgrade import util  # noqa: C415; pylint: disable=import-outside-toplevel

    repository = util.load_repositories_from('repo_path', '/etc/leapp/repo.d/', manager=None)
    with open(path.get_common_file_path(repository, LEAPP_UPGRADE_PATHS)) as f:
        upgrade_paths_map = json.loads(f.read())
    return upgrade_paths_map


def get_target_versions_from_config(src_version_id, flavor):
    """
    Retrieve all possible target versions from upgrade_paths_map.
    If no match is found returns empty list.
    """
    upgrade_paths_map = get_upgrade_paths_config()
    return upgrade_paths_map.get(flavor, {}).get(src_version_id, [])


def get_supported_target_versions(flavour=get_upgrade_flavour()):
    """
    Return a list of supported target versions for the given `flavour` of upgrade.
    The default value for `flavour` is `default`.
    """

    current_version_id = get_os_release_version_id('/etc/os-release')
    target_versions = get_target_versions_from_config(current_version_id, flavour)
    if not target_versions:
        # If we cannot find a particular major.minor version in the map,
        # we fallback to pick a target version just based on a major version.
        # This can happen for example when testing not yet released versions
        major_version = get_major_version(current_version_id)
        target_versions = get_target_versions_from_config(major_version, flavour)

    return target_versions


def get_target_version(flavour):
    target_versions = get_supported_target_versions(flavour)
    return target_versions[-1] if target_versions else None


def vet_upgrade_path(args):
    """
    Make sure the user requested upgrade_path is a supported one.
    If LEAPP_DEVEL_TARGET_RELEASE is set then it's value is not vetted against upgrade_paths_map but used as is.

    :raises: `CommandError` if the specified upgrade_path is not supported
    :return: `tuple` (target_release, flavor)
    """
    flavor = get_upgrade_flavour()
    env_version_override = os.getenv('LEAPP_DEVEL_TARGET_RELEASE')
    if env_version_override:
        check_version(env_version_override)
        return (env_version_override, flavor)
    target_release = args.target or get_target_version(flavor)
    supported_target_versions = get_supported_target_versions(flavor)
    if target_release not in supported_target_versions:
        raise CommandError(
                "Upgrade to {to} for {flavor} upgrade path is not supported, possible choices are {choices}".format(
                    to=target_release,
                    flavor=flavor,
                    choices=','.join(supported_target_versions)))
    return (target_release, flavor)
