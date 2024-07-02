from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DNFWorkaround, InstalledRPM

# maps target version to keys obsoleted in that version
OBSOLETED_KEYS_MAP = {
    7: [],
    8: [
        "gpg-pubkey-2fa658e0-45700c69",
        "gpg-pubkey-37017186-45761324",
        "gpg-pubkey-db42a60e-37ea5438",
    ],
    9: ["gpg-pubkey-d4082792-5b32db75"],
    10: [],
}


def _get_obsolete_keys():
    """
    Return keys obsoleted in target and previous versions
    """
    keys = []
    for version in range(7, int(get_target_major_version()) + 1):
        for key in OBSOLETED_KEYS_MAP[version]:
            name, version, release = key.rsplit("-", 2)
            if has_package(InstalledRPM, name, version=version, release=release):
                keys.append(key)

    return keys


def register_dnfworkaround(keys):
    api.produce(
        DNFWorkaround(
            display_name="remove obsolete RPM GPG keys from RPM DB",
            script_path=api.current_actor().get_common_tool_path("removerpmgpgkeys"),
            script_args=keys,
        )
    )


def process():
    keys = _get_obsolete_keys()
    if not keys:
        return

    register_dnfworkaround(keys)
