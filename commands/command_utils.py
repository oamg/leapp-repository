import hashlib
import json
import os
import re
import resource
from collections import namedtuple
from enum import Enum

from leapp.actors import config as actor_config
from leapp.exceptions import CommandError
from leapp.utils import audit, path

HANA_BASE_PATH = '/hana/shared'
HANA_SAPCONTROL_PATH_X86_64 = 'exe/linuxx86_64/hdb/sapcontrol'
HANA_SAPCONTROL_PATH_PPC64LE = 'exe/linuxppc64le/hdb/sapcontrol'

LEAPP_UPGRADE_FLAVOUR_DEFAULT = 'default'
LEAPP_UPGRADE_FLAVOUR_SAP_HANA = 'saphana'
LEAPP_UPGRADE_PATHS = 'upgrade_paths.json'


_VersionFormat = namedtuple('VersionFormat', ('human_readable', 'regex'))


class VersionFormats(Enum):
    MAJOR_ONLY = _VersionFormat('MAJOR_VER', re.compile(r'^[1-9]\d*$'))
    MAJOR_MINOR = _VersionFormat('MAJOR_VER.MINOR_VER', re.compile(r"^([1-9]\d*)\.(\d+)$"))


class _VersionKind(str, Enum):
    """ Enum encoding information whether the given OS version is source or target. """
    SOURCE = 'source'
    TARGET = 'target'


class DistroIDs(str, Enum):
    RHEL = 'rhel'
    CENTOS = 'centos'
    ALMALINUX = 'almalinux'


_DISTRO_VERSION_FORMATS = {
    DistroIDs.RHEL: VersionFormats.MAJOR_MINOR,
    DistroIDs.CENTOS: VersionFormats.MAJOR_ONLY,
    DistroIDs.ALMALINUX: VersionFormats.MAJOR_MINOR,
}
"""
Maps distro ID to the expected OS version format.

If a distro is not listed in the dictionary, then VersionFormats.MAJOR_MINOR
is used as a default.
"""


def assert_version_format(version_str, desired_format, version_kind):
    """
    Check whether a given version_str has the given desired format.

    In case the version does not conform to the desired_format, an CommandError will be raised.

    :raises: CommandError
    """
    if not re.match(desired_format.regex, version_str):
        error_str = (
            "Unexpected format of {} version: {}. The required format is '{}'."
        ).format(version_kind.value, version_str, desired_format.human_readable)
        raise CommandError(error_str)


def get_major_version_from_a_valid_version(version):
    """
    Return the major version from the given version string.

    Versioning schema: MAJOR.MINOR.PATCH

    :param str version: The version string according to the versioning schema described.
    :rtype: str
    :returns: The major version from the given version string.
    """
    return version.split('.')[0]


def _get_latest_version_with_matching_major_version(versions, major_version):
    """
    Find the latest version from given list of available versions matching the provided major version.

    Versioning schema: MAJOR.MINOR

    :param list[str] versions: List of versions to choose from.
    :param str major_version: The major version for which to find the latest version.
    :rtype: str
    :returns: Latest version with given major version form the given versions list, or empty string when not found.
    """
    latest_minor_version = -1
    for version in versions:
        version = version.split('.')
        if len(version) <= 1:
            continue  # skip versions without a minor version
        if version[0] == major_version:
            minor_version = int(version[1])
            latest_minor_version = max(minor_version, latest_minor_version)
    if latest_minor_version == -1:
        return ''
    return f'{major_version}.{latest_minor_version}'


def detect_sap_hana():
    """
    Detect SAP HANA based on existence of /hana/shared/*/exe/linuxx86_64/hdb/sapcontrol
    """
    if os.path.exists(HANA_BASE_PATH):
        for entry in os.listdir(HANA_BASE_PATH):
            # Does /hana/shared/{entry}/exe/linuxx86_64/hdb/sapcontrol exist?
            sap_on_intel = os.path.exists(os.path.join(HANA_BASE_PATH, entry, HANA_SAPCONTROL_PATH_X86_64))
            sap_on_power = os.path.exists(os.path.join(HANA_BASE_PATH, entry, HANA_SAPCONTROL_PATH_PPC64LE))
            if sap_on_intel or sap_on_power:
                return True
    return False


def get_upgrade_flavour():
    """
    Returns the flavour of the upgrade for this system.
    """
    if detect_sap_hana():
        return LEAPP_UPGRADE_FLAVOUR_SAP_HANA
    return LEAPP_UPGRADE_FLAVOUR_DEFAULT


def _retrieve_os_release_contents(_os_release_path='/etc/os-release', strip_double_quotes=True):
    """
    Retrieve the contents of /etc/os-release

    :rtype: dict[str, str]
    """
    with open(_os_release_path) as os_release_handle:
        lines = os_release_handle.readlines()

        os_release_contents = {}
        for line in lines:
            if '=' not in line:
                continue

            key, value = line.strip().split('=', 1)

            if strip_double_quotes:
                value = value.strip('"')

            os_release_contents[key] = value

        return os_release_contents


def get_os_release_version_id(filepath):
    """
    Retrieve data about System OS release from provided file.

    :return: `str` version_id
    """
    return _retrieve_os_release_contents(_os_release_path=filepath).get('VERSION_ID', '')


def get_source_distro_id():
    """
    Retrieve the OS release ID from /etc/os-release.

    :return: The OS release ID from /etc/os-release
    :rtype: str
    """
    return _retrieve_os_release_contents('/etc/os-release').get('ID', '')


def get_upgrade_paths_config():
    # NOTE(ivasilev) Importing here not to have circular dependencies
    from leapp.cli.commands.upgrade import util  # noqa: C415; pylint: disable=import-outside-toplevel

    repository = util.load_repositories_from('repo_path', '/etc/leapp/repo.d/', manager=None)
    with open(path.get_common_file_path(repository, LEAPP_UPGRADE_PATHS)) as f:
        upgrade_paths_map = json.loads(f.read())
    return upgrade_paths_map


def get_virtual_version_from_config(src_version_id, distro):
    """
    Retrieve the virtual version for the given version from upgrade_paths_map.

    :return: The virtual version or None if no match.
    """
    upgrade_paths_map = get_upgrade_paths_config()
    return upgrade_paths_map.get(distro, {}).get('_virtual_versions').get(src_version_id)


def get_supported_target_versions(target_distro, flavour=get_upgrade_flavour()):
    """
    Return a list of supported target versions for the given `flavour` of upgrade.
    The default value for `flavour` is `default`.

    :param str flavour: One of the upgrade flavours.
    :rtype: list[str]
    :returns: List of supported target versions.
    """
    os_release_contents = _retrieve_os_release_contents()
    current_version_id = os_release_contents.get('VERSION_ID', '')
    source_distro = os_release_contents.get('ID', '')

    # We want to guarantee our actors that if they see 'centos'/'rhel'/...
    # then they will always see expected version format
    expected_version_format = _DISTRO_VERSION_FORMATS.get(source_distro, VersionFormats.MAJOR_MINOR)
    assert_version_format(current_version_id, expected_version_format.value, _VersionKind.SOURCE)
    if source_distro == 'centos' and target_distro != 'centos':
        # when upconverting from centos, we need to lookup by virtual version
        current_version_id = get_virtual_version_from_config(current_version_id, source_distro)

    upgrade_paths_map = get_upgrade_paths_config()
    relevant_paths = upgrade_paths_map.get(source_distro, {}).get(flavour, {})
    target_versions = relevant_paths.get(current_version_id, [])
    if not target_versions:
        # If we cannot find a particular major.minor version in the map, we treat
        # the system as if it was the latest minor version of its major version
        # defined in the upgrade paths map. This can happen for example when
        # testing not yet released versions.
        available_source_versions = relevant_paths.keys()
        major_version = get_major_version_from_a_valid_version(current_version_id)
        latest_version = _get_latest_version_with_matching_major_version(available_source_versions, major_version)
        target_versions = relevant_paths.get(latest_version, [])
    return target_versions


def get_target_version(flavour, target_distro):
    target_versions = get_supported_target_versions(target_distro, flavour)
    return target_versions[-1] if target_versions else None


def get_target_release(args):
    """
    Return the user selected target release or choose one from config.

    A target release can be specified, ordered by priority, by the
    LEAPP_DEVEL_TARGET_RELEASE or args.target_version (--target cmdline arg) or
    in the config file.

    NOTE: when specified via the env var or cmdline arg, the version isn't
    checked against supported versions, this is done later by an actor in the
    upgrade process.

    :return: `tuple` (target_release, flavor)
    """
    flavor = get_upgrade_flavour()
    env_version_override = os.getenv('LEAPP_DEVEL_TARGET_RELEASE')

    target_ver = env_version_override or args.target_version
    target_distro_id = os.getenv('LEAPP_TARGET_OS')
    if target_ver:
        expected_version_format = _DISTRO_VERSION_FORMATS.get(
            target_distro_id, VersionFormats.MAJOR_MINOR
        )
        assert_version_format(target_ver, expected_version_format.value, _VersionKind.TARGET)
        return (target_ver, flavor)

    return (get_target_version(flavor, target_distro_id), flavor)


def set_resource_limits():
    """
    Set resource limits for the maximum number of open file descriptors and the maximum writable file size.

    :raises: `CommandError` if the resource limits cannot be set
    """

    def set_resource_limit(resource_type, soft, hard):
        rtype_string = (
            'open file descriptors' if resource_type == resource.RLIMIT_NOFILE
            else 'writable file size' if resource_type == resource.RLIMIT_FSIZE
            else 'unknown resource'
        )
        try:
            resource.setrlimit(resource_type, (soft, hard))
        except ValueError as err:
            raise CommandError(
                'Failure occurred while attempting to set soft limit higher than the hard limit. '
                'Resource type: {}, error: {}'.format(rtype_string, err)
            )
        except OSError as err:
            raise CommandError(
                'Failed to set resource limit. Resource type: {}, error: {}'.format(rtype_string, err)
            )

    soft_nofile, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
    soft_fsize, _ = resource.getrlimit(resource.RLIMIT_FSIZE)
    nofile_limit = 1024*16
    fsize_limit = resource.RLIM_INFINITY

    if soft_nofile < nofile_limit:
        set_resource_limit(resource.RLIMIT_NOFILE, nofile_limit, nofile_limit)

    if soft_fsize != fsize_limit:
        set_resource_limit(resource.RLIMIT_FSIZE, fsize_limit, fsize_limit)


def load_actor_configs_and_store_it_in_db(context, repositories, framework_cfg):
    """
    Load actor configuration so that actor's can access it and store it into leapp db.

    :param context: Current execution context
    :param repositories: Discovered repositories
    :param framework_cfg: Leapp's configuration
    """
    # Read the Actor Config and validate it against the schemas saved in the
    # configuration.

    actor_config_schemas = tuple(actor.config_schemas for actor in repositories.actors)
    actor_config_schemas = actor_config.normalize_schemas(actor_config_schemas)
    actor_config_path = framework_cfg.get('actor_config', 'path')

    # Note: actor_config.load() stores the loaded actor config into a global
    # variable which can then be accessed by functions in that file.  Is this
    # the right way to store that information?
    actor_cfg = actor_config.load(actor_config_path, actor_config_schemas)

    # Dump the collected configuration, checksum it and store it inside the DB
    config_text = json.dumps(actor_cfg)
    config_text_hash = hashlib.sha256(config_text.encode('utf-8')).hexdigest()
    config_data = audit.ActorConfigData(config=config_text, hash_id=config_text_hash)
    db_config = audit.ActorConfig(config=config_data, context=context)
    db_config.store()


def get_available_target_distro_ids():
    return [member.value for member in DistroIDs]
