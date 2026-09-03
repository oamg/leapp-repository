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
# The "install" set lists packages to (re)install without removing anything -
# packages the swap_distro_packages_workaround actor removes (to avoid a target
# file conflict) that must be brought back, with deps, by the upgrade
# transaction. Only packages already installed on the source system are added.
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
            "almalinux-backgrounds": "redhat-backgrounds",
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
    ("rocky", "rhel"): {
        "swap": {
            "rocky-logos": "redhat-logos",
            "rocky-logos-httpd": "redhat-logos-httpd",
            "rocky-logos-ipa": "redhat-logos-ipa",
            "rocky-indexhtml": "redhat-indexhtml",
            "rocky-backgrounds": "redhat-backgrounds",
            "rocky-release": "redhat-release",
        },
        "remove": {
            "rocky-repos",
            "rocky-gpg-keys",

            "rocky-release-*",
            "centos-release-*",
            "elrepo-release",
            "epel-release",
        },
    },
    ("ol", "rhel"): {
        "swap": {
            "oracle-logos": "redhat-logos",
            "oracle-logos-httpd": "redhat-logos-httpd",
            "oracle-logos-ipa": "redhat-logos-ipa",
            "oracle-indexhtml": "redhat-indexhtml",
            "oracle-backgrounds": "redhat-backgrounds",
            "oraclelinux-release": "redhat-release",
        },
        "remove": {
            "oraclelinux-release-el*",
            "oraclelinux-*-release-*",
        },
        "install": {
            "plymouth-theme-spinner",
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

    for pkg in config.get("install", {}):
        if pkg in rpms:
            to_install.add(pkg)

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

    # Oracle's redhat-release has a higher epoch than RHEL's, so dnf treats it as
    # newer and considers the RHEL redhat-release already satisfied; the
    # oraclelinux-release -> redhat-release swap above then never installs it.
    # Removing Oracle's redhat-release here lets the RHEL one in. For el9 -> el10
    # this must happen during the main upgrade (not the earlier isolated swap):
    # the el10 redhat-release requires a newer rpm than el9 provides, and rpm is
    # only upgraded once the repos are enabled, which is here. For el8 -> el9 it
    # is removed earlier by swap_distro_packages_workaround, where the el9
    # redhat-release installs against the el8 rpm.
    is_ol_to_rhel = (source_distro, target_distro) == ("ol", "rhel")
    if is_ol_to_rhel and get_target_major_version() == "10" and "redhat-release" in rpms:
        if "redhat-release" not in task.to_remove:
            task.to_remove.append("redhat-release")

    api.produce(task)
