import fnmatch

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import get_source_distro_id, get_target_distro_id
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, RpmTransactionTasks

# Config for swapping distribution-specific RPMs
# The keys can be in 2 "formats":
#     (<source_distro_id>, <target_distro_id>)
#     (<source_distro_id>, <target_distro_id>, <target_major_version as int>)
# The "swap" dict maps packages on the source distro to their replacements on
# the target distro
# The "remove" set lists packages or glob pattern for matching packages from
# the source distro to remove without any replacement.
_CONFIG = {
    ("centos", "rhel"): {
        "swap": {
            "centos-logos": "redhat-logos",
            "centos-logos-httpd": "redhat-logos-httpd",
            "centos-logos-ipa": "redhat-logos-ipa",
            "centos-indexhtml": "redhat-indexhtml",
            "centos-backgrounds": "redhat-backgrounds",
            "centos-stream-release": "redhat-release",
        },
        "remove": {
            "centos-gpg-keys",
            "centos-stream-repos",
            # various release packages, typically contain repofiles
            "centos-release-*",
            # present on Centos (not Stream) 8, let's include them if they are potentially leftover
            "centos-linux-release",
            "centos-linux-repos",
            "centos-obsolete-packages",
        },
    },
    ("almalinux", "rhel"): {
        "swap": {
            "almalinux-logos": "redhat-logos",
            "almalinux-logos-httpd": "redhat-logos-httpd",
            "almalinux-logos-ipa": "redhat-logos-ipa",
            "almalinux-indexhtml": "redhat-indexhtml",
            "almalinux-backgrouns": "redhat-backgrounds",
            "almalinux-release": "redhat-release",
        },
        "remove": {
            "almalinux-repos",
            "almalinux-gpg-keys",

            "almalinux-release-*",
            "centos-release-*",
            "elrepo-release",
            "epel-release",
        },
    },
}


def _get_config(source_distro, target_distro, target_major):
    key = (source_distro, target_distro, target_major)
    config = _CONFIG.get(key)
    if config:
        return config

    key = (source_distro, target_distro)
    return _CONFIG.get(key)


def _glob_match_rpms(rpms, pattern):
    return [rpm for rpm in rpms if fnmatch.fnmatch(rpm, pattern)]


def _make_transaction_tasks(config, rpms):
    to_install = set()
    to_remove = set()
    for source_pkg, target_pkg in config.get("swap", {}).items():
        if source_pkg in rpms:
            to_remove.add(source_pkg)
            to_install.add(target_pkg)

    for pkg in config.get("remove", {}):
        matches = _glob_match_rpms(rpms, pkg)
        to_remove.update(matches)

    return RpmTransactionTasks(to_install=list(to_install), to_remove=list(to_remove))


def process():
    rpms_msg = next(api.consume(DistributionSignedRPM), None)
    if not rpms_msg:
        raise StopActorExecutionError("Did not receive DistributionSignedRPM message")

    source_distro = get_source_distro_id()
    target_distro = get_target_distro_id()

    if source_distro == target_distro:
        return

    config = _get_config(source_distro, target_distro, get_target_major_version())
    if not config:
        api.current_logger().warning(
            "Could not find config for handling distro specific packages for {}->{} upgrade.".format(
                source_distro, target_distro
            )
        )
        return

    rpms = {rpm.name for rpm in rpms_msg.items}
    task = _make_transaction_tasks(config, rpms)
    api.produce(task)
