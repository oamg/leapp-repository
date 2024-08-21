from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.common.distro import get_distribution_data
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DNFWorkaround, InstalledRPM


def _get_obsolete_keys():
    """
    Return keys obsoleted in target and previous versions
    """
    distribution = api.current_actor().configuration.os_release.release_id
    obsoleted_keys_map = get_distribution_data(distribution).get('obsoleted-keys', {})
    keys = []
    for version in range(7, int(get_target_major_version()) + 1):
        try:
            for key in obsoleted_keys_map[str(version)]:
                name, version, release = key.rsplit("-", 2)
                if has_package(InstalledRPM, name, version=version, release=release):
                    keys.append(key)
        except KeyError:
            pass

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
