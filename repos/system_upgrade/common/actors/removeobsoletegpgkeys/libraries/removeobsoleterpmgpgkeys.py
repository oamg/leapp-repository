import itertools
import re

from leapp.configs.common.rhui import RHUI_CONFIG_SECTION, RhuiObsoleteGpgKeys, RhuiUseConfig
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import get_source_distro_id, get_target_distro_id
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.common.distro import get_distribution_data
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DNFWorkaround, InstalledRPM

_GPG_PUBKEY_NVR_FORMAT = re.compile(r"^gpg-pubkey-[0-9a-f]{8}-[0-9a-f]{8}$")


def _is_valid_pubkey_nvr(name):
    """
    Validate if a string is a valid gpg key RPM NVR
    """
    return _GPG_PUBKEY_NVR_FORMAT.match(name) is not None


def _is_key_installed(key):
    """
    :param key: The NVR of the gpg key RPM (e.g. gpg-pubkey-1d997668-61bae63b)
    """
    name, version, release = key.rsplit("-", 2)
    return has_package(InstalledRPM, name, version=version, release=release)


def _get_obsolete_keys():
    """
    Get keys obsoleted in target and previous major versions
    """
    distribution = get_target_distro_id()
    obsoleted_keys_map = get_distribution_data(distribution).get("obsoleted-keys", {})
    keys = []
    for version in range(7, int(get_target_major_version()) + 1):
        try:
            for key in obsoleted_keys_map[str(version)]:
                if _is_key_installed(key):
                    keys.append(key)
        except KeyError:
            pass

    return keys


def _get_source_distro_keys():
    """
    Get all known keys of the source distro

    This includes keys from all relevant previous OS versions as all of those
    might be present on the system.
    """
    distribution = get_source_distro_id()
    keys = get_distribution_data(distribution).get("keys", {})
    return [
        key
        for key in itertools.chain.from_iterable(keys.values())
        if _is_key_installed(key)
    ]


def _get_rhui_configured_keys():
    """
    Get obsolete cloud vendor keys specified in RHUI configuration.

    Returns keys only when RHUI use_config is True, ensuring this is opt-in behavior.
    Only returns keys that are actually installed on the system.
    """
    rhui_config = api.current_actor().config[RHUI_CONFIG_SECTION]

    # Only apply RHUI keys when the leapp RHUI configuration is set
    if not rhui_config[RhuiUseConfig.name]:
        api.current_logger().debug("RHUI config disabled, ignoring obsolete RPM GPG keys")
        return []

    configured_keys = rhui_config[RhuiObsoleteGpgKeys.name]

    for key in configured_keys:
        if not _is_valid_pubkey_nvr(key):
            raise StopActorExecutionError(
                "Provided RHUI config contains invalid value for setting {}".format(
                    RhuiObsoleteGpgKeys.name
                ),
                details={
                    "details": "Entry {} is not a in valid RPM GPG name".format(key),
                    "hint": (
                        "The expected format is: gpg-pubkey-<version>-<release>,"
                        " for example: gpg-pubkey-d4082792-5b32db75"
                    ),
                },
            )

    return [key for key in configured_keys if _is_key_installed(key)]


def register_dnfworkaround(keys):
    api.produce(
        DNFWorkaround(
            display_name="remove obsolete RPM GPG keys from RPM DB",
            script_path=api.current_actor().get_common_tool_path("removerpmgpgkeys"),
            script_args=list(keys),
        )
    )


def _get_all_obsolete_keys():
    if get_source_distro_id() == get_target_distro_id():
        # only upgrading - remove keys obsoleted in previous versions
        keys = _get_obsolete_keys()
    else:
        # also converting - we need to remove all keys from the source distro
        keys = _get_source_distro_keys()

    keys.extend(_get_rhui_configured_keys())
    return set(keys)


def process():
    keys = _get_all_obsolete_keys()
    if keys:
        register_dnfworkaround(keys)
