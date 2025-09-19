import itertools

from leapp.libraries.common.config import get_source_distro_id, get_target_distro_id
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.common.distro import get_distribution_data
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DNFWorkaround, InstalledRPM


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


def register_dnfworkaround(keys):
    api.produce(
        DNFWorkaround(
            display_name="remove obsolete RPM GPG keys from RPM DB",
            script_path=api.current_actor().get_common_tool_path("removerpmgpgkeys"),
            script_args=keys,
        )
    )


def process():
    if get_source_distro_id() == get_target_distro_id():
        # only upgrading - remove keys obsoleted in previous versions
        keys = _get_obsolete_keys()
    else:
        # also converting - we need to remove all keys from the source distro
        keys = _get_source_distro_keys()

    if keys:
        register_dnfworkaround(keys)
